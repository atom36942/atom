"""Atom MDM functions. Plain data, explicit dependencies, no shared mutable state."""

def func_mdm_json_read(value, fallback=None):
    """Decode a database JSON value without changing the input."""
    import json
    return json.loads(value) if isinstance(value, str) else (value if value is not None else fallback)

def func_mdm_row_serialize(row):
    """Return an API-safe copy of one database row."""
    import json
    from fastapi.encoders import jsonable_encoder
    if row is None:
        return None
    result = dict(row)
    for key in ("addresses", "registrations", "roles", "role_flags", "cw_role_flags", "account_groups", "statistics", "cw_comparison_statistics", "payload", "prepared_data", "evidence"):
        if key in result:
            result[key] = json.loads(result[key]) if isinstance(result[key], str) else result[key]
    return jsonable_encoder(result)


def func_mdm_command_validate(*, body: dict) -> dict:
    """Validate and copy a review command into a plain dictionary; no database access."""
    import copy
    from uuid import UUID
    from fastapi import HTTPException

    defaults = {"request_id": None, "source": None, "run_id": None, "action": None,
                "reason": None, "case_ids": [], "parts": [], "approved_id": None,
                "version": None, "cw_code": None, "comparison_id": None,
                "confirmed": False, "organization_name": None, "addresses": None}
    if not isinstance(body, dict) or set(body) - set(defaults):
        raise HTTPException(status_code=400, detail="Invalid review fields.")
    cmd = copy.deepcopy(defaults | body)
    for key in ("request_id", "run_id", "comparison_id"):
        if key == "comparison_id" and cmd[key] is None:
            continue
        try:
            cmd[key] = UUID(str(cmd[key]))
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(status_code=400, detail=f"Invalid {key.replace('_', ' ')}.")
    if cmd["source"] not in ("CW", "SAP"):
        raise HTTPException(status_code=400, detail="Source must be CW or SAP.")
    if cmd["action"] not in ("approve", "split", "keep_separate", "reject_suggestion",
                             "confirm_existing", "approve_new", "reject_match", "correct",
                             "record_success", "record_failure"):
        raise HTTPException(status_code=400, detail="Unknown review action.")
    if not isinstance(cmd["reason"], str) or not 3 <= len(cmd["reason"]) <= 4000 or len(cmd["reason"].strip()) < 3:
        raise HTTPException(status_code=400, detail="Please enter a review note (3–4,000 characters).")
    for key in ("approved_id", "version"):
        if cmd[key] is not None and (type(cmd[key]) is not int or not 1 <= cmd[key] <= 9223372036854775807):
            raise HTTPException(status_code=400, detail=f"Invalid {key.replace('_', ' ')}.")
    for key, maximum in (("cw_code", 100), ("organization_name", 500)):
        if cmd[key] is not None and (not isinstance(cmd[key], str) or len(cmd[key]) > maximum):
            raise HTTPException(status_code=400, detail=f"Invalid {key.replace('_', ' ')}.")
    if type(cmd["confirmed"]) is not bool:
        raise HTTPException(status_code=400, detail="Confirmed must be true or false.")
    if not isinstance(cmd["case_ids"], list) or len(cmd["case_ids"]) > 100:
        raise HTTPException(status_code=400, detail="Select at most 100 proposed groups.")
    try:
        cmd["case_ids"] = [func_mdm_case_id(value) for value in cmd["case_ids"]]
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid proposed group ID.")
    if not isinstance(cmd["parts"], list) or len(cmd["parts"]) > 2000:
        raise HTTPException(status_code=400, detail="Invalid final groups.")
    normalized = []
    for part in cmd["parts"]:
        if not isinstance(part, dict) or set(part) - {"entity_ids", "organization_name", "selected_cw_code", "final_record"}:
            raise HTTPException(status_code=400, detail="Invalid final group fields.")
        ids, name, cw_code = part.get("entity_ids"), part.get("organization_name"), part.get("selected_cw_code")
        if not isinstance(ids, list) or not 1 <= len(ids) <= 2000 or any(not isinstance(value, str) or not value.strip() for value in ids):
            raise HTTPException(status_code=400, detail="Each final group needs valid source IDs.")
        if not isinstance(name, str) or not name.strip() or len(name) > 500:
            raise HTTPException(status_code=400, detail="Each final group needs a company name (maximum 500 characters).")
        if cw_code is not None and (not isinstance(cw_code, str) or len(cw_code) > 100):
            raise HTTPException(status_code=400, detail="Invalid surviving CargoWise code.")
        normalized.append({"entity_ids": ids, "organization_name": name, "selected_cw_code": cw_code, "final_record": part.get("final_record")})
    cmd["parts"] = normalized
    if cmd["addresses"] is not None and (not isinstance(cmd["addresses"], list) or len(cmd["addresses"]) > 2000 or any(not isinstance(a, dict) for a in cmd["addresses"])):
        raise HTTPException(status_code=400, detail="Addresses must be a list of address objects.")
    return cmd

def func_mdm_query_validate(*, params: dict) -> dict:
    """Normalize source, pagination and literal text search without changing params."""
    from fastapi import HTTPException
    source = params.get("source", "CW")
    if source not in ("CW", "SAP"):
        raise HTTPException(status_code=400, detail="Source must be CW or SAP.")
    try:
        page = max(1, min(100000, int(params.get("page", 1))))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid page.")
    query = str(params.get("q", "")).strip()[:200]
    search = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    pending = params.get("pending", True)
    if not isinstance(pending, bool):
        value = str(pending).strip().lower()
        if value not in ("true", "1", "yes", "on", "ok", "false", "0", "no", "off"):
            raise HTTPException(status_code=400, detail="Invalid pending filter.")
        pending = value in ("true", "1", "yes", "on", "ok")
    return {"source": source, "prefix": source.lower(), "page": page, "query": query, "search": search, "pending": pending}

async def func_mdm_read(*, app_state, pool, kind: str, params: dict) -> dict:
    """Dispatch an allowed read through Atom's registered functions."""
    from fastapi import HTTPException
    if kind not in ("overview", "groups", "detail", "candidates", "cw-search", "approved", "audit", "matches", "company"):
        raise HTTPException(status_code=404, detail="Unknown MDM operation.")
    func_read = getattr(app_state, "func_mdm_read_" + kind.replace("-", "_"))
    from asyncpg import LockNotAvailableError
    try:
        result = await func_read(app_state=app_state, pool=pool, params=params)
        if kind in ("groups", "detail", "candidates"):
            result = app_state.func_mdm_case_fields(value=result)
        return result
    except LockNotAvailableError as exc:
        raise HTTPException(status_code=503, detail="Data refresh in progress. Please try again shortly.", headers={"Retry-After": "30"}) from exc

async def func_mdm_read_overview(*, app_state, pool, params: dict) -> dict:
    """Read overview with a supplied pool; callable without the API or dispatcher."""
    from fastapi import HTTPException
    from uuid import UUID
    options = app_state.func_mdm_query_validate(params=params)
    source, prefix, page, query, search = (options[key] for key in ("source", "prefix", "page", "query", "search"))
    async with pool.acquire() as conn:
        async with conn.transaction():
            if not await conn.fetchval("SELECT pg_try_advisory_xact_lock_shared(hashtext('mdm_fresh_publication'))"):
                raise HTTPException(status_code=503, detail="Data refresh in progress. Please try again shortly.", headers={"Retry-After": "30"})
            await conn.execute("SET LOCAL lock_timeout='1s'")
            await conn.execute("SET LOCAL statement_timeout='25s'")
            await conn.execute("SET LOCAL jit=off")
            queue = await conn.fetchrow("SELECT count(*) approved_records FROM mdm_approved_master a JOIN mdm_runs_current r USING(run_id) WHERE r.source=$1", source)
            review = app_state.func_mdm_row_serialize(queue)
            review["decisions"] = await conn.fetchval("SELECT count(*) FROM mdm_review_decision d JOIN mdm_runs_current r USING(run_id) WHERE r.source=$1", source)
            review["name_exceptions"] = await conn.fetchval(f"SELECT count(*) FROM {prefix}_source_current WHERE NOT eligible")
            review["pending_business_cases"] = await conn.fetchval("""
                SELECT count(*) FROM mdm_review_case m
                JOIN mdm_runs_current r ON r.run_id=m.run_id
                WHERE r.source=$1 AND m.source_record_count>1
                  AND NOT EXISTS (
                    SELECT 1 FROM mdm_review_case_member sm
                    JOIN mdm_approved_member am USING(run_id,entity_id)
                    WHERE sm.run_id=m.run_id AND sm.case_id=m.case_id
                  )""", source)
            return {"review": review, "comparison": app_state.func_mdm_row_serialize(await conn.fetchrow("SELECT comparison_id,sap_run_id,cw_run_id,comparison_is_current,completed_at FROM mdm_sap_cw_comparison_current"))}

async def func_mdm_read_groups(*, app_state, pool, params: dict) -> dict:
    """Read groups with a supplied pool; callable without the API or dispatcher."""
    from fastapi import HTTPException
    from uuid import UUID
    options = app_state.func_mdm_query_validate(params=params)
    source, prefix, page, query, search = (options[key] for key in ("source", "prefix", "page", "query", "search"))
    async with pool.acquire() as conn:
        async with conn.transaction():
            if not await conn.fetchval("SELECT pg_try_advisory_xact_lock_shared(hashtext('mdm_fresh_publication'))"):
                raise HTTPException(status_code=503, detail="Data refresh in progress. Please try again shortly.", headers={"Retry-After": "30"})
            await conn.execute("SET LOCAL lock_timeout='1s'")
            await conn.execute("SET LOCAL statement_timeout='25s'")
            await conn.execute("SET LOCAL jit=off")
            mode = params.get("mode", "duplicates")
            if mode not in ("duplicates", "all", "exceptions"):
                raise HTTPException(status_code=400, detail="Unknown list mode.")
            if mode == "exceptions":
                rows = await conn.fetch(f"SELECT * FROM {prefix}_source_current WHERE NOT eligible AND (original_name ILIKE $1 OR source_code ILIKE $1) ORDER BY entity_id LIMIT 26 OFFSET $2", search, (page-1)*25)
            else:
                run_id=await conn.fetchval("SELECT run_id FROM mdm_runs_current WHERE source=$1",source)
                rows = await conn.fetch("""WITH reviewed AS MATERIALIZED (
                  SELECT DISTINCT m.case_id FROM mdm_approved_member a
                  JOIN mdm_review_case_member m USING(run_id,entity_id) WHERE a.run_id=$1
                ), page AS MATERIALIZED (
                  SELECT m.run_id,m.case_id golden_id,m.organization_name,m.source_record_count,m.is_customer,m.is_vendor,m.cw_codes,
                    EXISTS(SELECT 1 FROM reviewed r WHERE r.case_id=m.case_id) reviewed
                  FROM mdm_review_case m WHERE m.run_id=$1 AND ($2='all' OR m.source_record_count>1)
                  AND (m.organization_name ILIKE $3 OR m.case_id::text=$4 OR EXISTS(SELECT 1 FROM unnest(m.cw_codes) c WHERE c ILIKE $3))
                  AND ($5::boolean=false OR NOT EXISTS(SELECT 1 FROM reviewed r WHERE r.case_id=m.case_id))
                  ORDER BY m.source_record_count DESC,m.organization_name,m.case_id LIMIT 26 OFFSET $6
                ) SELECT page.*,coalesce(p.cw_match_status,'not_compared') cw_match_status,p.possible_cw_codes,c.comparison_is_current cw_comparison_is_current
                  FROM page LEFT JOIN mdm_sap_cw_comparison_current c ON c.sap_run_id=page.run_id
                  LEFT JOIN mdm_sap_cw_presence p ON p.comparison_id=c.comparison_id AND p.sap_master_id=page.golden_id
                  ORDER BY page.source_record_count DESC,page.organization_name,page.golden_id""",run_id,mode,search,query,options["pending"],(page-1)*25)
            return {"rows": [app_state.func_mdm_row_serialize(x) for x in rows[:25]], "has_more": len(rows)>25, "page": page}

async def func_mdm_read_detail(*, app_state, pool, params: dict) -> dict:
    """Read detail with a supplied pool; callable without the API or dispatcher."""
    from fastapi import HTTPException
    from uuid import UUID
    options = app_state.func_mdm_query_validate(params=params)
    source, prefix, page, query, search = (options[key] for key in ("source", "prefix", "page", "query", "search"))
    async with pool.acquire() as conn:
        async with conn.transaction():
            if not await conn.fetchval("SELECT pg_try_advisory_xact_lock_shared(hashtext('mdm_fresh_publication'))"):
                raise HTTPException(status_code=503, detail="Data refresh in progress. Please try again shortly.", headers={"Retry-After": "30"})
            await conn.execute("SET LOCAL lock_timeout='1s'")
            await conn.execute("SET LOCAL statement_timeout='25s'")
            await conn.execute("SET LOCAL jit=off")
            try:
                ids = list(dict.fromkeys(func_mdm_case_id(x) for x in params.get("ids", "").split(",") if x))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid group ID.")
            if not 1 <= len(ids) <= 100:
                raise HTTPException(status_code=400, detail="Select between 1 and 100 proposed groups.")
            masters = await conn.fetch(f"SELECT * FROM {prefix}_master_current WHERE golden_id=ANY($1::bigint[])", ids)
            if len(masters) != len(ids):
                raise HTTPException(status_code=409, detail="A selected group is no longer current. Refresh the list.")
            records = await conn.fetch(f"SELECT s.*,a.approved_id FROM {prefix}_source_current s LEFT JOIN mdm_approved_member a USING(run_id,entity_id) WHERE s.golden_id=ANY($1::bigint[]) ORDER BY s.golden_id,s.entity_id LIMIT 2001", ids)
            if len(records)>2000:
                raise HTTPException(status_code=400, detail="This selection has more than 2,000 records. Select fewer groups.")
            links = await conn.fetch("SELECT l.* FROM mdm_review_case_link l JOIN mdm_review_case_member m ON m.run_id=l.run_id AND m.entity_id=l.left_entity_id WHERE m.run_id=$1 AND m.case_id=ANY($2::bigint[]) LIMIT 150", masters[0]["run_id"], ids)
            return {"masters": [app_state.func_mdm_row_serialize(x) for x in masters], "records": [app_state.func_mdm_row_serialize(x) for x in records], "evidence": [app_state.func_mdm_row_serialize(x) for x in links], "evidence_limit": 150}

async def func_mdm_read_candidates(*, app_state, pool, params: dict) -> dict:
    """Read candidates with a supplied pool; callable without the API or dispatcher."""
    from fastapi import HTTPException
    from uuid import UUID
    options = app_state.func_mdm_query_validate(params=params)
    source, prefix, page, query, search = (options[key] for key in ("source", "prefix", "page", "query", "search"))
    async with pool.acquire() as conn:
        async with conn.transaction():
            if not await conn.fetchval("SELECT pg_try_advisory_xact_lock_shared(hashtext('mdm_fresh_publication'))"):
                raise HTTPException(status_code=503, detail="Data refresh in progress. Please try again shortly.", headers={"Retry-After": "30"})
            await conn.execute("SET LOCAL lock_timeout='1s'")
            await conn.execute("SET LOCAL statement_timeout='25s'")
            await conn.execute("SET LOCAL jit=off")
            name = query.upper()
            if not name:
                raise HTTPException(status_code=400, detail="Enter a cleaned company name to find similar-name cases.")
            run=await conn.fetchrow("SELECT * FROM mdm_runs_current WHERE source=$1",source)
            rows = await conn.fetch("""WITH searched AS MATERIALIZED (
                SELECT n.name_id FROM mdm_review_name n JOIN mdm_source_name s ON s.name_id=n.name_id AND s.run_id=$1
                WHERE n.review_run_id=$2 AND n.name_key LIKE $3
              ), pairs AS (
                SELECT p.left_name_id,p.right_name_id,p.name_similarity,'pg_trgm'::text similarity_method FROM mdm_review_name_pair p
                JOIN searched s ON s.name_id=p.left_name_id WHERE p.review_run_id=$2
                UNION
                SELECT p.left_name_id,p.right_name_id,p.name_similarity,'pg_trgm'::text FROM mdm_review_name_pair p
                JOIN searched s ON s.name_id=p.right_name_id WHERE p.review_run_id=$2
                UNION
                SELECT p.left_name_id,p.right_name_id,p.name_similarity,'rapidfuzz_legacy'::text FROM mdm_source_candidate_extra p
                WHERE p.name_review_run_id=$2 AND (p.left_name_id IN (SELECT name_id FROM searched) OR p.right_name_id IN (SELECT name_id FROM searched))
              ) SELECT p.*,count(*) OVER() total_matches,ln.name_key left_name,rn.name_key right_name,
                l.source_records left_record_count,r.source_records right_record_count,l.master_ids left_golden_ids,r.master_ids right_golden_ids
                FROM pairs p JOIN mdm_source_name l ON l.run_id=$1 AND l.name_id=p.left_name_id
                JOIN mdm_source_name r ON r.run_id=$1 AND r.name_id=p.right_name_id
                JOIN mdm_review_name ln ON ln.name_id=p.left_name_id JOIN mdm_review_name rn ON rn.name_id=p.right_name_id
                WHERE p.left_name_id<>p.right_name_id OR l.source_records>1
                ORDER BY p.left_name_id,p.right_name_id LIMIT 26 OFFSET $4""",run["run_id"],run["name_review_run_id"],"%"+name.replace("%","\\%").replace("_","\\_")+"%",(page-1)*25)
            return {"rows": [app_state.func_mdm_row_serialize(x) for x in rows[:25]], "has_more":len(rows)>25, "page":page, "total":rows[0]["total_matches"] if rows else 0}

async def func_mdm_read_cw_search(*, app_state, pool, params: dict) -> dict:
    """Read cw search with a supplied pool; callable without the API or dispatcher."""
    from fastapi import HTTPException
    from uuid import UUID
    options = app_state.func_mdm_query_validate(params=params)
    source, prefix, page, query, search = (options[key] for key in ("source", "prefix", "page", "query", "search"))
    async with pool.acquire() as conn:
        async with conn.transaction():
            if not await conn.fetchval("SELECT pg_try_advisory_xact_lock_shared(hashtext('mdm_fresh_publication'))"):
                raise HTTPException(status_code=503, detail="Data refresh in progress. Please try again shortly.", headers={"Retry-After": "30"})
            await conn.execute("SET LOCAL lock_timeout='1s'")
            await conn.execute("SET LOCAL statement_timeout='25s'")
            await conn.execute("SET LOCAL jit=off")
            if len(query)<2:
                return {"rows":[]}
            masters=await conn.fetch("SELECT golden_id FROM cw_master_current WHERE organization_name ILIKE $1 OR EXISTS(SELECT 1 FROM unnest(cw_codes) c WHERE c ILIKE $1) ORDER BY organization_name,golden_id LIMIT 51",search)
            rows = await conn.fetch("SELECT entity_id,cw_code,original_name,cleaned_name,addresses,is_active,is_customer,is_vendor FROM cw_source_current WHERE golden_id=ANY($1::bigint[]) ORDER BY cw_code LIMIT 51", [x["golden_id"] for x in masters])
            return {"rows":[app_state.func_mdm_row_serialize(x) for x in rows[:50]], "has_more":len(rows)>50}

async def func_mdm_read_approved(*, app_state, pool, params: dict) -> dict:
    """Read approved with a supplied pool; callable without the API or dispatcher."""
    from fastapi import HTTPException
    from uuid import UUID
    options = app_state.func_mdm_query_validate(params=params)
    source, prefix, page, query, search = (options[key] for key in ("source", "prefix", "page", "query", "search"))
    async with pool.acquire() as conn:
        async with conn.transaction():
            if not await conn.fetchval("SELECT pg_try_advisory_xact_lock_shared(hashtext('mdm_fresh_publication'))"):
                raise HTTPException(status_code=503, detail="Data refresh in progress. Please try again shortly.", headers={"Retry-After": "30"})
            await conn.execute("SET LOCAL lock_timeout='1s'")
            await conn.execute("SET LOCAL statement_timeout='25s'")
            await conn.execute("SET LOCAL jit=off")
            rows=await conn.fetch("SELECT * FROM mdm_approved_current WHERE source=$1 AND organization_name ILIKE $2 ORDER BY id DESC LIMIT 26 OFFSET $3",source,search,(page-1)*25)
            return {"rows":[app_state.func_mdm_row_serialize(x) for x in rows[:25]], "has_more":len(rows)>25,"page":page}

async def func_mdm_read_audit(*, app_state, pool, params: dict) -> dict:
    """Read audit with a supplied pool; callable without the API or dispatcher."""
    from fastapi import HTTPException
    from uuid import UUID
    options = app_state.func_mdm_query_validate(params=params)
    source, prefix, page, query, search = (options[key] for key in ("source", "prefix", "page", "query", "search"))
    async with pool.acquire() as conn:
        async with conn.transaction():
            if not await conn.fetchval("SELECT pg_try_advisory_xact_lock_shared(hashtext('mdm_fresh_publication'))"):
                raise HTTPException(status_code=503, detail="Data refresh in progress. Please try again shortly.", headers={"Retry-After": "30"})
            await conn.execute("SET LOCAL lock_timeout='1s'")
            await conn.execute("SET LOCAL statement_timeout='25s'")
            await conn.execute("SET LOCAL jit=off")
            rows=await conn.fetch("SELECT * FROM mdm_review_decision WHERE source=$1 ORDER BY id DESC LIMIT 26 OFFSET $2",source,(page-1)*25)
            return {"rows":[app_state.func_mdm_row_serialize(x) for x in rows[:25]],"has_more":len(rows)>25,"page":page}

async def func_mdm_read_matches(*, app_state, pool, params: dict) -> dict:
    """Read matches with a supplied pool; callable without the API or dispatcher."""
    from fastapi import HTTPException
    from uuid import UUID
    options = app_state.func_mdm_query_validate(params=params)
    source, prefix, page, query, search = (options[key] for key in ("source", "prefix", "page", "query", "search"))
    async with pool.acquire() as conn:
        async with conn.transaction():
            if not await conn.fetchval("SELECT pg_try_advisory_xact_lock_shared(hashtext('mdm_fresh_publication'))"):
                raise HTTPException(status_code=503, detail="Data refresh in progress. Please try again shortly.", headers={"Retry-After": "30"})
            await conn.execute("SET LOCAL lock_timeout='1s'")
            await conn.execute("SET LOCAL statement_timeout='25s'")
            await conn.execute("SET LOCAL jit=off")
            try:
                aid=int(params.get("id",0))
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail="Invalid approved ID.")
            if aid <= 0:
                raise HTTPException(status_code=400, detail="Invalid approved ID.")
            master=await conn.fetchrow("SELECT * FROM mdm_approved_current WHERE id=$1 AND source='SAP'",aid)
            if not master:
                raise HTTPException(status_code=404, detail="SAP approved record not found.")
            rows=await conn.fetch("""SELECT DISTINCT p.cw_name_id,p.name_similarity,n.name_key cw_name,w.entity_ids cw_source_ids
                FROM mdm_sap_cw_comparison_current c JOIN mdm_review_case_member m ON m.run_id=c.sap_run_id
                JOIN mdm_sap_cw_name_match p ON p.comparison_id=c.comparison_id AND p.sap_name_id=m.name_id
                JOIN mdm_review_name n ON n.name_id=p.cw_name_id
                JOIN mdm_source_name w ON w.run_id=c.cw_run_id AND w.name_id=p.cw_name_id
                WHERE m.entity_id=ANY($1::text[]) ORDER BY p.name_similarity DESC LIMIT 101""",master["source_entity_ids"])
            # Include exact original OrgCodes and addresses, with a bounded response.
            eids=list(dict.fromkeys(e for r in rows[:100] for e in r["cw_source_ids"]))
            records=await conn.fetch("SELECT entity_id,cw_code,original_name,addresses,is_active FROM cw_source_current WHERE entity_id=ANY($1::text[]) ORDER BY cw_code LIMIT 501",eids)
            return {"master":app_state.func_mdm_row_serialize(master),"candidates":[app_state.func_mdm_row_serialize(x) for x in rows[:100]],"records":[app_state.func_mdm_row_serialize(x) for x in records[:500]],"truncated":len(rows)>100 or len(records)>500,"comparison":app_state.func_mdm_row_serialize(await conn.fetchrow("SELECT comparison_id,comparison_is_current FROM mdm_sap_cw_comparison_current"))}

def func_mdm_validate_parts(*, records, parts, action, source):
    """Every source row must appear exactly once; survivors must belong to their part."""
    from fastapi import HTTPException
    expected={r["entity_id"] for r in records}
    actual=[e for p in parts for e in p["entity_ids"]]
    if len(actual)!=len(set(actual)) or set(actual)!=expected:
        raise HTTPException(status_code=400, detail="Assign every source record to exactly one final group.")
    if action=="approve" and len(parts)!=1:
        raise HTTPException(status_code=400, detail="Approve merge must produce one final group.")
    if action=="keep_separate" and any(len(p["entity_ids"])!=1 for p in parts):
        raise HTTPException(status_code=400, detail="Keep separate must produce one final group per source record.")
    if action=="split" and len(parts)<2:
        raise HTTPException(status_code=400, detail="Split requires at least two final groups.")
    by_id={r["entity_id"]:r for r in records}
    for part in parts:
        if not part["organization_name"].strip():
            raise HTTPException(status_code=400, detail="Each final group needs a usable company name.")
        if source=="CW":
            codes={by_id[e]["cw_code"] for e in part["entity_ids"]}
            if not part["selected_cw_code"] or part["selected_cw_code"] not in codes:
                raise HTTPException(status_code=400, detail="Choose a surviving CargoWise code from each final group's source records.")
        elif part["selected_cw_code"]:
            raise HTTPException(status_code=400, detail="Confirm SAP-to-CargoWise matches in the separate matching step.")


def func_mdm_values_union(*, records, key: str) -> list:
    """Copy address/registration values with their source IDs; never mutate inputs."""
    import copy
    import json
    result=[]
    for r in records:
        values = json.loads(r[key]) if isinstance(r[key], str) else r[key]
        for value in values or []:
            # Retain source attribution even if values are equal.
            result.append({**copy.deepcopy(value),"source_entity_id":r["entity_id"]})
    return result


def func_mdm_boolean_union(*, records, key: str):
    """Combine nullable role flags without treating unknown as false."""
    values=[r[key] for r in records]
    return True if True in values else (None if None in values else False)


async def func_mdm_decision_create(*, conn, cmd: dict, actor: dict, digest: str):
    """Append an audit event using the caller's transaction and validated data."""
    import json
    return await conn.fetchval("""INSERT INTO mdm_review_decision
        (request_id,request_hash,source,run_id,action,actor_id,actor_name,reason,payload)
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb) RETURNING id""",
        cmd["request_id"],digest,cmd["source"],cmd["run_id"],cmd["action"],actor["id"],actor.get("username") or str(actor["id"]),cmd["reason"].strip(),json.dumps(cmd, ensure_ascii=False, separators=(",", ":"), default=str))


async def func_mdm_write(*, app_state, pool, actor: dict, body: dict) -> dict:
    """Apply a review atomically; resolve helper functions through Atom app_state."""
    import hashlib
    import json
    from uuid import uuid4
    from fastapi import HTTPException
    cmd = app_state.func_mdm_command_validate(body=body)
    prefix = cmd["source"].lower()
    digest = hashlib.sha256(json.dumps(cmd, ensure_ascii=False, separators=(",", ":"), default=str).encode()).hexdigest()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL statement_timeout='30s'")
            await conn.execute("SET LOCAL jit=off")
            if not await conn.fetchval("SELECT pg_try_advisory_xact_lock_shared(hashtext('mdm_fresh_publication'))"):
                raise HTTPException(status_code=409, detail="New review data is being published. Refresh and try again shortly.")
            await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended($1,0))",str(cmd["request_id"]))
            previous=await conn.fetchrow("SELECT id,request_hash,actor_id FROM mdm_review_decision WHERE request_id=$1",cmd["request_id"])
            if previous:
                if previous["request_hash"]!=digest or previous["actor_id"]!=actor["id"]:
                    raise HTTPException(status_code=409, detail="This request ID has already been used for a different action.")
                return {"decision_id":previous["id"],"replayed":True}
            current=await conn.fetchval("SELECT run_id FROM mdm_runs_current WHERE source=$1",cmd["source"])
            if current!=cmd["run_id"]:
                raise HTTPException(status_code=409, detail="The source run changed. Refresh before reviewing.")
            if cmd["action"] in ("approve","split","keep_separate"):
                ids=sorted(set(cmd["case_ids"]))
                if not ids:
                    raise HTTPException(status_code=400, detail="Select at least one proposed group.")
                masters=await conn.fetch("SELECT case_id FROM mdm_review_case WHERE run_id=$1 AND case_id=ANY($2::bigint[]) ORDER BY case_id FOR UPDATE",cmd["run_id"],ids)
                if len(masters)!=len(ids):
                    raise HTTPException(status_code=400, detail="A selected group does not belong to this source/run.")
                records=await conn.fetch(f"SELECT * FROM {prefix}_source_current WHERE golden_id=ANY($1::bigint[]) ORDER BY entity_id LIMIT 2001",ids)
                if len(records)>2000:
                    raise HTTPException(status_code=400, detail="Select fewer than 2,001 records.")
                claimed=await conn.fetchval("SELECT count(*) FROM mdm_approved_member WHERE run_id=$1 AND entity_id=ANY($2::text[])",cmd["run_id"],[r["entity_id"] for r in records])
                if claimed:
                    raise HTTPException(status_code=409, detail="Another review has already approved some of these records. Refresh the list.")
                app_state.func_mdm_validate_parts(records=records,parts=cmd["parts"],action=cmd["action"],source=cmd["source"])
                final_records = [app_state.func_mdm_final_record_prepare(
                    records=[r for r in records if r["entity_id"] in part["entity_ids"]],
                    final_record=part.get("final_record"), source=cmd["source"]
                ) for part in cmd["parts"]]
                event=await app_state.func_mdm_decision_create(conn=conn, cmd=cmd, actor=actor, digest=digest)
                approved=[]
                for part, final in zip(cmd["parts"], final_records):
                    selected=[r for r in records if r["entity_id"] in set(part["entity_ids"])]
                    roles={"source_roles":[{"entity_id":r["entity_id"],"cw_roles":app_state.func_mdm_json_read(r["cw_role_flags"],{}),"account_group_code":r["account_group_code"],"account_group_name":r["account_group_name"]} for r in selected]}
                    roles["approved_flags"] = final["role_flags"]
                    roles["final_record_reviewed"] = True
                    roles["registration_conflicts_confirmed"] = final["registration_conflicts_confirmed"]
                    roles["no_address_confirmed"] = final["no_address_confirmed"]
                    aid=await conn.fetchval("""INSERT INTO mdm_approved_master
                        (golden_id,source,run_id,decision_id,organization_name,source_master_ids,source_entity_ids,cw_codes,selected_cw_code,is_customer,is_vendor,addresses,registrations,roles,destination_status,approved_by)
                        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::jsonb,$13::jsonb,$14::jsonb,$15,$16) RETURNING id""",
                        uuid4(),cmd["source"],cmd["run_id"],event,part["organization_name"].strip(),list({r["golden_id"] for r in selected}),part["entity_ids"],
                        sorted({r["cw_code"] for r in selected if r["cw_code"]}),part["selected_cw_code"],
                        final["is_customer"],final["is_vendor"],json.dumps(final["addresses"]),json.dumps(final["registrations"]),json.dumps(roles),"update" if cmd["source"]=="CW" else "pending",actor["id"])
                    await conn.executemany("INSERT INTO mdm_approved_member(run_id,entity_id,approved_id) VALUES($1,$2,$3)",[(cmd["run_id"],e,aid) for e in part["entity_ids"]])
                    approved.append(aid)
                return {"decision_id":event,"approved_ids":approved}
            if cmd["action"]=="reject_suggestion":
                if not cmd["case_ids"] or len(set(cmd["case_ids"]))<2:
                    raise HTTPException(status_code=400, detail="Select at least two proposed groups to reject their suggested combination.")
                count=await conn.fetchval("SELECT count(*) FROM mdm_review_case WHERE run_id=$1 AND case_id=ANY($2::bigint[])",cmd["run_id"],cmd["case_ids"])
                if count!=len(set(cmd["case_ids"])):
                    raise HTTPException(status_code=400, detail="Invalid proposed group selection.")
                return {"decision_id":await app_state.func_mdm_decision_create(conn=conn, cmd=cmd, actor=actor, digest=digest)}
            master=await conn.fetchrow("SELECT * FROM mdm_approved_master WHERE id=$1 FOR UPDATE",cmd["approved_id"])
            if not master or master["source"]!=cmd["source"] or master["run_id"]!=cmd["run_id"]:
                raise HTTPException(status_code=404, detail="Approved record not found in this source/run.")
            if master["version"]!=cmd["version"]:
                raise HTTPException(status_code=409, detail="This record was changed by another reviewer. Refresh and try again.")
            if await conn.fetchval("SELECT EXISTS(SELECT 1 FROM mdm_execution_result WHERE approved_id=$1 AND status='success')",master["id"]):
                raise HTTPException(status_code=409, detail="This action is already recorded as completed in CargoWise.")
            if cmd["action"] in ("confirm_existing","approve_new","reject_match"):
                if cmd["source"]!="SAP":
                    raise HTTPException(status_code=400, detail="Destination matching is available only for SAP records.")
                comparison=await conn.fetchrow("SELECT * FROM mdm_sap_cw_comparison_current")
                if not comparison or not comparison["comparison_is_current"] or comparison["comparison_id"]!=cmd["comparison_id"]:
                    raise HTTPException(status_code=409, detail="The CargoWise comparison changed or is stale. Refresh it before deciding.")
                if cmd["action"] in ("confirm_existing","reject_match"):
                    exists=await conn.fetchval("SELECT EXISTS(SELECT 1 FROM cw_source_current WHERE cw_code=$1)",cmd["cw_code"])
                    if not exists:
                        raise HTTPException(status_code=400, detail="Choose a valid CargoWise code from the current snapshot.")
                if cmd["action"]=="approve_new" and not cmd["confirmed"]:
                    raise HTTPException(status_code=400, detail="Confirm that you checked the CargoWise matches and search results.")
                event=await app_state.func_mdm_decision_create(conn=conn, cmd=cmd, actor=actor, digest=digest)
                status={"confirm_existing":"existing","approve_new":"new","reject_match":"pending"}[cmd["action"]]
                await conn.execute("UPDATE mdm_approved_master SET destination_status=$2,selected_cw_code=$3,comparison_id=$4,version=version+1,updated_at=now() WHERE id=$1",master["id"],status,cmd["cw_code"] if status=="existing" else None,cmd["comparison_id"])
                return {"decision_id":event,"destination_status":status}
            if cmd["action"]=="correct":
                if not cmd["organization_name"] or not cmd["organization_name"].strip():
                    raise HTTPException(status_code=400, detail="A corrected company name is required.")
                addresses=cmd["addresses"] if cmd["addresses"] is not None else app_state.func_mdm_json_read(master["addresses"],[])
                # Address edits keep source linkage; do not silently discard original addresses.
                old=app_state.func_mdm_json_read(master["addresses"],[])
                if len(addresses)!=len(old) or any(a.get("source_entity_id")!=b.get("source_entity_id") for a,b in zip(addresses,old)):
                    raise HTTPException(status_code=400, detail="Preserve every address and its source_entity_id when correcting details.")
                if app_state.func_mdm_json_read(master["roles"],{}).get("final_record_reviewed"):
                    if any(a.get("source_index")!=b.get("source_index") for a,b in zip(addresses,old)):
                        raise HTTPException(status_code=400, detail="Preserve the original address references.")
                    if addresses and (any(type(a.get("is_primary")) is not bool for a in addresses) or sum(a["is_primary"] for a in addresses)!=1):
                        raise HTTPException(status_code=400, detail="Keep exactly one primary address.")
                event=await app_state.func_mdm_decision_create(conn=conn, cmd=cmd, actor=actor, digest=digest)
                await conn.execute("UPDATE mdm_approved_master SET organization_name=$2,addresses=$3::jsonb,destination_status=$4,comparison_id=NULL,version=version+1,updated_at=now() WHERE id=$1",master["id"],cmd["organization_name"].strip(),json.dumps(addresses),"pending" if cmd["source"]=="SAP" else "update")
                return {"decision_id":event}
            if cmd["action"] in ("record_success","record_failure"):
                view=await conn.fetchrow("SELECT * FROM mdm_approved_current WHERE id=$1",master["id"])
                if not view["ready_for_export"]:
                    raise HTTPException(status_code=409, detail="This record is not approved for a current CargoWise update/import.")
                if cmd["action"]=="record_success" and not (cmd["cw_code"] or "").strip():
                    raise HTTPException(status_code=400, detail="Enter the resulting CargoWise OrgCode.")
                if cmd["action"]=="record_success" and cmd["source"]=="CW" and cmd["cw_code"]!=master["selected_cw_code"]:
                    raise HTTPException(status_code=400, detail="The result must use the approved surviving CargoWise code.")
                if cmd["action"]=="record_success" and cmd["source"]=="SAP" and await conn.fetchval("SELECT EXISTS(SELECT 1 FROM cw_source_current WHERE cw_code=$1)",cmd["cw_code"]):
                    raise HTTPException(status_code=400, detail="That code already exists in the snapshot. Confirm an existing match instead.")
                if cmd["action"]=="record_success" and cmd["source"]=="SAP":
                    await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended($1,0))","mdm-result:"+cmd["cw_code"])
                    used=await conn.fetchval("SELECT EXISTS(SELECT 1 FROM mdm_execution_result WHERE status='success' AND cw_code=$1 AND approved_id<>$2)",cmd["cw_code"],master["id"])
                    if used:
                        raise HTTPException(status_code=409, detail="That CargoWise code is already recorded against another completed master.")
                event=await app_state.func_mdm_decision_create(conn=conn, cmd=cmd, actor=actor, digest=digest)
                await conn.execute("INSERT INTO mdm_execution_result(approved_id,decision_id,approved_version,status,cw_code,details,recorded_by) VALUES($1,$2,$3,$4,$5,$6,$7)",master["id"],event,master["version"],"success" if cmd["action"]=="record_success" else "failed",cmd["cw_code"],cmd["reason"],actor["id"])
                await conn.execute("UPDATE mdm_approved_master SET version=version+1,updated_at=now() WHERE id=$1",master["id"])
                return {"decision_id":event}
            raise HTTPException(status_code=400, detail="Unknown review action.")


async def func_mdm_export(*, app_state, pool, source: str):
    """Export approved handoff data using the supplied pool and Atom row formatter."""
    import csv
    import io
    import json
    from fastapi import HTTPException
    from fastapi.responses import Response
    if source not in ("CW", "SAP"):
        raise HTTPException(status_code=400, detail="Source must be CW or SAP.")
    # Controlled handoff file, not a claim of CargoWise native import compatibility.
    from asyncpg import LockNotAvailableError
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                if not await conn.fetchval("SELECT pg_try_advisory_xact_lock_shared(hashtext('mdm_fresh_publication'))"):
                    raise HTTPException(status_code=503, detail="Data refresh in progress. Please try again shortly.", headers={"Retry-After": "30"})
                await conn.execute("SET LOCAL lock_timeout='1s'")
                await conn.execute("SET LOCAL statement_timeout='25s'")
                rows=await conn.fetch("SELECT * FROM mdm_approved_current WHERE source=$1 AND ready_for_export ORDER BY id LIMIT 10001",source)
    except LockNotAvailableError as exc:
        raise HTTPException(status_code=503, detail="Data refresh in progress. Please try again shortly.", headers={"Retry-After": "30"}) from exc
    if len(rows)>10000:
        raise HTTPException(status_code=400, detail="Export exceeds 10,000 approved records; use a controlled batch export.")
    fields=["id","golden_id","organization_name","source_entity_ids","cw_codes","selected_cw_code","is_customer","is_vendor","addresses","registrations","roles","destination_status","version"]
    output=io.StringIO();writer=csv.writer(output);writer.writerow(fields)
    for row in rows:
        values=[]
        data=app_state.func_mdm_row_serialize(row)
        for key in fields:
            value=data[key]
            value=json.dumps(value,ensure_ascii=False) if isinstance(value,(list,dict)) else str(value) if value is not None else ""
            if value.lstrip().startswith(("=","+","-","@")) or value.startswith(("\t","\r","\n")):
                value="'"+value
            values.append(value)
        writer.writerow(values)
    return Response("\ufeff"+output.getvalue(),media_type="text/csv",headers={"Content-Disposition":f'attachment; filename="{source.lower()}_approved_handoff.csv"',"Cache-Control":"no-store"})



def func_mdm_case_fields(*, value):
    """Use case terminology in proposal responses; approved golden IDs are separate."""
    names = {"golden_id": "case_id", "masters": "cases", "left_golden_ids": "left_case_ids", "right_golden_ids": "right_case_ids"}
    if isinstance(value, list):
        return [func_mdm_case_fields(value=item) for item in value]
    if isinstance(value, dict):
        return {names.get(key, key): func_mdm_case_fields(value=item) for key, item in value.items()}
    return value


def func_mdm_case_id(value):
    """Validate a numeric PostgreSQL case identity without accepting floats or booleans."""
    if type(value) not in (int, str) or not str(value).isascii() or not str(value).isdigit():
        raise ValueError("Invalid case ID")
    number = int(value)
    if not 1 <= number <= 9223372036854775807:
        raise ValueError("Invalid case ID")
    return number


async def func_mdm_read_company(*, app_state, pool, params: dict) -> dict:
    """Read one imported source company, including its original source fields."""
    import json
    from fastapi import HTTPException
    options = app_state.func_mdm_query_validate(params=params)
    try:
        raw_id = func_mdm_case_id(params.get("id"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid company record.")
    async with pool.acquire() as conn:
        async with conn.transaction():
            if not await conn.fetchval("SELECT pg_try_advisory_xact_lock_shared(hashtext('mdm_fresh_publication'))"):
                raise HTTPException(status_code=503, detail="Data refresh in progress. Please try again shortly.")
            await conn.execute("SET LOCAL lock_timeout='1s'")
            await conn.execute("SET LOCAL statement_timeout='25s'")
            if options["source"] == "CW":
                record = await conn.fetchval('SELECT to_jsonb(o) FROM cw_raw_organization o WHERE id=$1', raw_id)
                if record is None:
                    raise HTTPException(status_code=404, detail="Company record not found. Refresh the review list.")
                record = json.loads(record) if isinstance(record, str) else record
                addresses = await conn.fetchval("SELECT coalesce(jsonb_agg(to_jsonb(a)),'[]'::jsonb) FROM cw_raw_address a WHERE \"OA_OH\"=$1::uuid", record["OH_PK"])
                registrations = await conn.fetchval("SELECT coalesce(jsonb_agg(to_jsonb(r)),'[]'::jsonb) FROM cw_raw_registration r WHERE \"OK_OH\"=$1::uuid", record["OH_PK"])
                return {"company": record, "addresses": json.loads(addresses) if isinstance(addresses,str) else addresses, "registrations": json.loads(registrations) if isinstance(registrations,str) else registrations}
            record = await conn.fetchval('SELECT to_jsonb(o) FROM sap_raw_organization o WHERE id=$1', raw_id)
            if record is None:
                raise HTTPException(status_code=404, detail="Company record not found. Refresh the review list.")
            return {"company": json.loads(record) if isinstance(record,str) else record}


async def func_mdm_export_cases(*, app_state, pool, params: dict):
    """Download current cases as flat source-record rows, without pagination."""
    import csv
    import io
    import json
    from fastapi import HTTPException
    from fastapi.responses import StreamingResponse
    options = app_state.func_mdm_query_validate(params=params)
    source, prefix = options['source'], options['prefix']
    status = params.get('status', 'pending')
    if status not in ('pending', 'approved', 'all'):
        raise HTTPException(status_code=400, detail='Invalid export status.')
    async with pool.acquire() as conn:
        async with conn.transaction():
            if not await conn.fetchval("SELECT pg_try_advisory_xact_lock_shared(hashtext('mdm_fresh_publication'))"):
                raise HTTPException(status_code=503, detail='Data refresh in progress. Please try again shortly.')
            await conn.execute("SET LOCAL lock_timeout='1s'")
            await conn.execute("SET LOCAL statement_timeout='60s'")
            await conn.execute("SET LOCAL jit=off")
            rows = await conn.fetch(f"""
                WITH current_run AS MATERIALIZED (SELECT run_id FROM mdm_runs_current WHERE source=$1),
                reviewed AS MATERIALIZED (
                  SELECT DISTINCT cm.case_id FROM mdm_approved_member am
                  JOIN mdm_review_case_member cm USING(run_id,entity_id)
                  WHERE am.run_id=(SELECT run_id FROM current_run)
                ), cases AS MATERIALIZED (
                  SELECT c.* FROM mdm_review_case c
                  WHERE c.run_id=(SELECT run_id FROM current_run)
                  AND (c.source_record_count>1 OR c.case_id IN (SELECT case_id FROM reviewed))
                  AND (c.organization_name ILIKE $2 OR c.case_id::text=$3
                    OR EXISTS(SELECT 1 FROM unnest(c.cw_codes) code WHERE code ILIKE $2))
                  AND ($4='all' OR ($4='approved')=(c.case_id IN (SELECT case_id FROM reviewed)))
                )
                SELECT c.case_id golden_id,cm.entity_id,cm.is_customer,cm.is_vendor,
                  i.prepared_data->>'cw_code' cw_code,i.prepared_data->>'source_code' source_code,
                  i.prepared_data->>'source_file' source_file,i.prepared_data->>'original_name' original_name,
                  i.prepared_data->>'account_group_name' account_group_name,
                  i.prepared_data->'addresses' addresses,i.prepared_data->'registrations' registrations,
                  c.source_record_count,c.organization_name proposed_name,
                  a.organization_name approved_name,a.selected_cw_code,a.id approved_record_id,
                  a.approved_at,d.actor_name,d.action,d.reason
                FROM cases c JOIN mdm_review_case_member cm ON cm.run_id=c.run_id AND cm.case_id=c.case_id
                JOIN mdm_match_input i ON i.run_id=cm.input_run_id AND i.entity_id=cm.entity_id
                LEFT JOIN mdm_approved_member am ON am.run_id=cm.run_id AND am.entity_id=cm.entity_id
                LEFT JOIN mdm_approved_master a ON a.id=am.approved_id
                LEFT JOIN mdm_review_decision d ON d.id=a.decision_id
                ORDER BY c.source_record_count DESC,c.organization_name,c.case_id,cm.entity_id
                """, source, options['search'], options['query'], status)
    def decoded(value):
        return json.loads(value) if isinstance(value, str) else value or []
    address_count = max((len(decoded(r['addresses'])) for r in rows), default=1)
    fields = ['Case ID','Status','Records in case','Source','Source record ID','Source code','Source file',
              'Company name','Proposed company name','Account type','Account group','Registration numbers',
              'Approved record ID','Approved company name','CargoWise code to keep','Reviewer','Review date','Decision','Reason']
    for i in range(1,address_count+1):
        fields += [f'Address {i}',f'City {i}',f'State {i}',f'Postcode {i}',f'Country {i}']
    def safe(value):
        value = '' if value is None else str(value)
        if value.lstrip().startswith(('=','+','-','@')) or value.startswith(('\t','\r','\n')):
            value = "'" + value
        return value
    def generate():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        yield '\ufeff'
        writer.writerow(fields)
        yield buffer.getvalue(); buffer.seek(0); buffer.truncate(0)
        for r in rows:
            account = 'Customer & vendor' if r['is_customer'] and r['is_vendor'] else 'Customer' if r['is_customer'] else 'Vendor' if r['is_vendor'] else 'Unclassified'
            registrations = '; '.join(' | '.join(str(v) for v in (x.get('scheme'),x.get('country'),x.get('normalized')) if v) for x in decoded(r['registrations']))
            values = [r['golden_id'],'Approved' if r['approved_record_id'] else 'Pending',r['source_record_count'],source,r['entity_id'],r['cw_code'] or r['source_code'],r['source_file'],r['original_name'],r['proposed_name'],account,r['account_group_name'],registrations,r['approved_record_id'],r['approved_name'],r['selected_cw_code'],r['actor_name'],r['approved_at'],r['action'],r['reason']]
            addresses = decoded(r['addresses'])
            for i in range(address_count):
                a = addresses[i] if i<len(addresses) else {}
                lines = a.get('lines', '')
                values += [' | '.join(str(x) for x in lines) if isinstance(lines,list) else lines,a.get('city'),a.get('state'),a.get('postcode'),a.get('country')]
            writer.writerow([safe(v) for v in values])
            if buffer.tell() >= 65536:
                yield buffer.getvalue(); buffer.seek(0); buffer.truncate(0)
        if buffer.tell():
            yield buffer.getvalue()
    return StreamingResponse(generate(), media_type='text/csv', headers={
        'Content-Disposition':f'attachment; filename="{source.lower()}_{status}_cases.csv"','Cache-Control':'no-store'})


def func_mdm_final_record_prepare(*, records, final_record, source):
    """Validate reviewed fields and retain server-owned source provenance."""
    import copy
    import re
    from fastapi import HTTPException
    allowed = {'confirmed','addresses','registrations','role_flags','is_customer','is_vendor',
               'no_address_confirmed','registration_conflicts_confirmed'}
    if not isinstance(final_record, dict) or set(final_record) != allowed or final_record['confirmed'] is not True:
        raise HTTPException(status_code=400, detail='Preview and confirm the final record before approval.')
    for key in ('no_address_confirmed','registration_conflicts_confirmed'):
        if type(final_record[key]) is not bool:
            raise HTTPException(status_code=400, detail='Invalid final-record confirmation.')
    for key in ('is_customer','is_vendor'):
        if final_record[key] is not None and type(final_record[key]) is not bool:
            raise HTTPException(status_code=400, detail='Customer/vendor flags must be Yes, No or Unknown.')
    by_id = {r['entity_id']: r for r in records}
    result = copy.deepcopy(final_record)
    for kind in ('addresses','registrations'):
        items = final_record[kind]
        if not isinstance(items,list) or len(items)>10000:
            raise HTTPException(status_code=400, detail=f'Invalid final {kind}.')
        result[kind] = []
        seen = set()
        for item in items:
            fields = {'lines','city','state','postcode','country','is_primary'} if kind=='addresses' else {'scheme','country','normalized'}
            if not isinstance(item,dict) or set(item) != fields | {'source_entity_id','source_index'}:
                raise HTTPException(status_code=400, detail=f'Invalid reviewed {kind} fields.')
            eid, index = item['source_entity_id'], item['source_index']
            if not isinstance(eid,str) or eid not in by_id or type(index) is not int or index<0 or (eid,index) in seen:
                raise HTTPException(status_code=400, detail='Each retained detail must belong to this final group, once only.')
            original = func_mdm_json_read(by_id[eid][kind], [])
            if index>=len(original):
                raise HTTPException(status_code=400, detail='Source details changed. Reopen the review.')
            seen.add((eid,index))
            retained = copy.deepcopy(original[index])
            for field in fields-{'lines','is_primary'}:
                value = item[field]
                if not isinstance(value,str) or len(value)>1000:
                    raise HTTPException(status_code=400, detail=f'Invalid {field} in final {kind}.')
                retained[field] = value.strip()
            if retained['country'] and not re.fullmatch('[A-Za-z]{2}',retained['country']):
                raise HTTPException(status_code=400, detail='Use a two-letter country code, or leave it blank.')
            retained['country'] = retained['country'].upper()
            if kind=='addresses':
                if type(item['is_primary']) is not bool or not isinstance(item['lines'],list) or len(item['lines'])>20 or any(not isinstance(v,str) or len(v)>1000 for v in item['lines']):
                    raise HTTPException(status_code=400, detail='Invalid final address.')
                retained['lines'] = [v.strip() for v in item['lines'] if v.strip()]
                retained['is_primary'] = item['is_primary']
                if not any(retained.get(k) for k in ('lines','city','state','postcode','country')):
                    raise HTTPException(status_code=400, detail='Correct or exclude empty addresses.')
                # Matching keys describe source data, not reviewer corrections.
                for key in ('city_key','postcode_key','components'):
                    retained.pop(key,None)
            else:
                if not retained['normalized']:
                    raise HTTPException(status_code=400, detail='Enter a registration number or exclude that registration.')
                if any(retained.get(k)!=original[index].get(k) for k in ('scheme','country','normalized')):
                    retained['verified'] = False
                retained.pop('match_key',None)
            retained['source_entity_id'], retained['source_index'] = eid,index
            result[kind].append(retained)
    if result['addresses'] and sum(a['is_primary'] for a in result['addresses'])!=1:
        raise HTTPException(status_code=400, detail='Choose exactly one primary address for each final company.')
    if not result['addresses'] and not final_record['no_address_confirmed']:
        raise HTTPException(status_code=400, detail='Confirm saving without an address, or retain an address.')
    # Different countries/types may legitimately have different registration numbers.
    registrations = {}
    for r in result['registrations']:
        registrations.setdefault((r['scheme'].upper(),r['country']),set()).add(re.sub(r'\W','',r['normalized'].upper()))
    if any(len(v)>1 for v in registrations.values()) and not final_record['registration_conflicts_confirmed']:
        raise HTTPException(status_code=400, detail='Resolve or explicitly confirm different registration numbers for the same type and country.')
    flags = final_record['role_flags']
    known = set().union(*(func_mdm_json_read(r['cw_role_flags'],{}).keys() for r in records)) if source=='CW' else set()
    if not isinstance(flags,dict) or set(flags)!=known or any(v is not None and type(v) is not bool for v in flags.values()):
        raise HTTPException(status_code=400, detail='Confirm every source role flag using Yes, No or Unknown.')
    return result
