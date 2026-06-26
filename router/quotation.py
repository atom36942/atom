from fastapi import APIRouter, Request

# router
router = APIRouter()

# api
@router.post("/quotation/my-rate-create")
async def func_api_quotation_rates_create(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    table = "rates"
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    if not isinstance(obj_list, list) or not obj_list: raise Exception("obj_list required")
    if len(obj_list) > 5000: raise Exception("maximum 5000 rates allowed")
    if any(not isinstance(obj, dict) for obj in obj_list): raise Exception("object data invalid")
    obj_list = [dict(obj) for obj in obj_list]
    for obj in obj_list:
        obj.pop("id", None)
        obj.pop("created_by_id", None)
        obj.pop("updated_by_id", None)
        obj.pop("deactivated_by_id", None)
        obj["created_by_id"] = request.state.user["id"]
    result = await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_buffer_limit_default, mode="now", table=table, obj_list=obj_list)
    return {"status": 1, "message": result}

@router.put("/quotation/my-rate-update")
async def func_api_quotation_rates_update(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    table = "rates"
    created_by_id = None if int(request.state.user.get("role") or 0) == 1 else request.state.user["id"]
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[])
    obj_list = ob.get("obj_list", [ob])
    if not isinstance(obj_list, list) or not obj_list: raise Exception("obj_list required")
    if len(obj_list) > 5000: raise Exception("maximum 5000 rates allowed")
    if any(not isinstance(obj, dict) for obj in obj_list): raise Exception("object data invalid")
    obj_list = [dict(obj) for obj in obj_list]
    for obj in obj_list:
        if "id" not in obj: raise Exception("id required for rate update")
        if len(obj) < 2: raise Exception("at least one rate field required for update")
        obj.pop("created_by_id", None)
        obj.pop("deactivated_by_id", None)
        if "deactivated_at" in obj and obj.get("deactivated_at") is not None: obj["deactivated_by_id"] = request.state.user["id"]
        obj["updated_by_id"] = request.state.user["id"]
    result = []
    obj_group = {}
    for obj in obj_list:
        obj_group.setdefault(tuple(sorted(obj.keys())), []).append(obj)
    for group_list in obj_group.values():
        group_result = await app_state.func_postgres_update(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, config_regex=app_state.config_regex, table=table, obj_list=group_list, created_by_id=created_by_id)
        result.extend(group_result if isinstance(group_result, list) else [])
    return {"status": 1, "message": result}

@router.post("/quotation/my-rate-delete")
async def func_api_quotation_rates_delete(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    table = "rates"
    created_by_id = None if int(request.state.user.get("role") or 0) == 1 else request.state.user["id"]
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("ids", "list:int", 1, None, None)])
    result = await app_state.func_postgres_delete(client_postgres=app_state.client_postgres, client_postgres_conn=None, cache_postgres_schema=app_state.cache_postgres_schema, table=table, ids=ob["ids"], created_by_id=created_by_id)
    return {"status": 1, "message": result}

@router.get("/quotation/rate-read")
async def func_api_quotation_rates_read(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_read_fallback: raise Exception("postgres read client not initialized")
    table = "rates"
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("order", "str", 0, None, "id desc"), ("filter", "list", 0, None, [])])
    ol = await app_state.func_postgres_read(client_postgres=app_state.client_postgres_read_fallback, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_postgres_where_build=app_state.func_postgres_where_build, func_postgres_relation=app_state.func_postgres_relation, cache_postgres_schema=app_state.cache_postgres_schema, config_sql_read_limit_max=app_state.config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=app_state.config_sql_read_relation_fetch_limit_max, table=table, filter=oq["filter"], limit=oq["limit"] + 1, page=oq["page"], order=oq["order"], column="*", relation=[])
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.post("/quotation/my-create")
async def func_api_quotation_quotations_create(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres or not app_state.client_postgres_read_fallback: raise Exception("postgres client not initialized")
    table = "quotations"
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("rate_id", "bigint", 1, None, None), ("customer_name", "str", 1, None, None), ("customer_email", "str", 0, None, None), ("customer_mobile", "str", 0, None, None), ("quoted_rate", "numeric", 1, None, None), ("status", "int", 0, [1, 2], 1), ("remarks", "str", 0, None, None)])
    async with app_state.client_postgres_read_fallback.acquire() as conn:
        rate = await conn.fetchrow("select id, min_sell_rate from rates where id=$1 and deactivated_at is null", int(ob["rate_id"]))
        if not rate: raise Exception("active rate not found")
        if float(ob["quoted_rate"]) < float(rate["min_sell_rate"] or 0): raise Exception("quoted_rate cannot be below minimum sell rate")
    obj = {
        "created_by_id": request.state.user["id"],
        "updated_by_id": request.state.user["id"],
        "rate_id": ob.get("rate_id"),
        "customer_name": ob.get("customer_name"),
        "customer_email": ob.get("customer_email"),
        "customer_mobile": ob.get("customer_mobile"),
        "quoted_rate": ob.get("quoted_rate"),
        "status": ob.get("status"),
        "remarks": ob.get("remarks"),
    }
    result = await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_buffer_limit_default, mode="now", table=table, obj_list=[obj])
    return {"status": 1, "message": result}

@router.put("/quotation/my-update")
async def func_api_quotation_quotations_update(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres or not app_state.client_postgres_read_fallback: raise Exception("postgres client not initialized")
    table = "quotations"
    is_admin = int(request.state.user.get("role") or 0) == 1
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("id", "bigint", 1, None, None), ("rate_id", "bigint", 0, None, None), ("customer_name", "str", 0, None, None), ("customer_email", "str", 0, None, None), ("customer_mobile", "str", 0, None, None), ("quoted_rate", "numeric", 0, None, None), ("status", "int", 0, [1, 2], None), ("remarks", "str", 0, None, None)])
    async with app_state.client_postgres_read_fallback.acquire() as conn:
        if is_admin:
            quote = await conn.fetchrow("select * from quotations where id=$1", int(ob["id"]))
        else:
            quote = await conn.fetchrow("select * from quotations where id=$1 and created_by_id=$2", int(ob["id"]), request.state.user["id"])
        if not quote: raise Exception("quotation not found")
        if int(quote["status"] or 0) == 3: raise Exception("approved quotation cannot be changed")
        rate_id = int(ob["rate_id"] if ob.get("rate_id") is not None else quote["rate_id"])
        quoted_rate = ob["quoted_rate"] if ob.get("quoted_rate") is not None else quote["quoted_rate"]
        rate = await conn.fetchrow("select id, min_sell_rate from rates where id=$1 and deactivated_at is null", rate_id)
        if not rate: raise Exception("active rate not found")
        if float(quoted_rate) < float(rate["min_sell_rate"] or 0): raise Exception("quoted_rate cannot be below minimum sell rate")
    obj = {
        "id": ob["id"],
        "updated_by_id": request.state.user["id"],
        "rate_id": ob["rate_id"] if ob.get("rate_id") is not None else quote["rate_id"],
        "customer_name": ob["customer_name"] if ob.get("customer_name") is not None else quote["customer_name"],
        "customer_email": ob["customer_email"] if ob.get("customer_email") is not None else quote["customer_email"],
        "customer_mobile": ob["customer_mobile"] if ob.get("customer_mobile") is not None else quote["customer_mobile"],
        "quoted_rate": ob["quoted_rate"] if ob.get("quoted_rate") is not None else quote["quoted_rate"],
        "status": ob["status"] if ob.get("status") is not None else quote["status"],
        "remarks": ob["remarks"] if ob.get("remarks") is not None else quote["remarks"],
    }
    result = await app_state.func_postgres_update(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, config_regex=app_state.config_regex, table=table, obj_list=[obj], created_by_id=None if is_admin else request.state.user["id"])
    return {"status": 1, "message": result}

@router.post("/quotation/my-delete")
async def func_api_quotation_quotations_delete(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres or not app_state.client_postgres_read_fallback: raise Exception("postgres client not initialized")
    table = "quotations"
    is_admin = int(request.state.user.get("role") or 0) == 1
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("ids", "list:int", 1, None, None)])
    async with app_state.client_postgres_read_fallback.acquire() as conn:
        if is_admin:
            rows = await conn.fetch("select id, status from quotations where id = any($1::bigint[])", ob["ids"])
        else:
            rows = await conn.fetch("select id, status from quotations where id = any($1::bigint[]) and created_by_id=$2", ob["ids"], request.state.user["id"])
        if len(rows) != len(set(ob["ids"])): raise Exception("quotation not found")
        if any(int(row["status"] or 0) != 1 for row in rows): raise Exception("only draft quotations can be deleted")
    result = await app_state.func_postgres_delete(client_postgres=app_state.client_postgres, client_postgres_conn=None, cache_postgres_schema=app_state.cache_postgres_schema, table=table, ids=ob["ids"], created_by_id=None if is_admin else request.state.user["id"])
    return {"status": 1, "message": result}

@router.put("/quotation/decision")
async def func_api_quotation_quotations_decision(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("id", "bigint", 1, None, None), ("status", "int", 1, [3, 4], None), ("decision_remarks", "str", 0, None, None)])
    async with app_state.client_postgres.acquire() as conn:
        quote = await conn.fetchrow("select * from quotations where id=$1", int(ob["id"]))
        if not quote: raise Exception("quotation not found")
        if int(quote["status"] or 0) != 2: raise Exception("only submitted quotations can be approved or rejected")
        rate = await conn.fetchrow("select id, min_sell_rate from rates where id=$1 and deactivated_at is null", int(quote["rate_id"]))
        if not rate: raise Exception("active rate not found")
        if float(quote["quoted_rate"]) < float(rate["min_sell_rate"] or 0): raise Exception("quoted_rate cannot be below minimum sell rate")
        row = await conn.fetchrow("update quotations set status=$1, decision_remarks=$2, approved_at=now(), approved_by_id=$3, updated_at=now(), updated_by_id=$3 where id=$4 returning *", ob["status"], ob.get("decision_remarks"), request.state.user["id"], int(ob["id"]))
    return {"status": 1, "message": dict(row)}

@router.get("/quotation/my-read")
async def func_api_quotation_quotations_my_read(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_read_fallback: raise Exception("postgres read client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("status", "int", 0, [1, 2, 3, 4], None), ("customer_name", "str", 0, None, None)])
    values, where = [request.state.user["id"]], ["q.created_by_id=$1"]
    if oq.get("status"):
        values.append(oq["status"])
        where.append(f"q.status=${len(values)}")
    if oq.get("customer_name"):
        values.append(f"%{oq['customer_name']}%")
        where.append(f"q.customer_name ilike ${len(values)}")
    where_sql = f"where {' and '.join(where)}" if where else ""
    values.extend([oq["limit"] + 1, (oq["page"] - 1) * oq["limit"]])
    sql = f"""
        select q.*, r.mode, r.origin, r.destination, r.carrier, r.commodity, r.charge_unit, r.currency, r.min_sell_rate, r.origin_charges, r.destination_charges, r.transit_days, r.remarks as rate_remarks, q.quoted_rate + coalesce(r.origin_charges, 0) + coalesce(r.destination_charges, 0) as final_quote_amount
        from quotations q
        left join rates r on r.id = q.rate_id
        {where_sql}
        order by q.id desc
        limit ${len(values)-1} offset ${len(values)}
    """
    async with app_state.client_postgres_read_fallback.acquire() as conn:
        rows = await conn.fetch(sql, *values)
    ol = [dict(row) for row in rows]
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}

@router.get("/quotation/read")
async def func_api_quotation_quotations_read(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_read_fallback: raise Exception("postgres read client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, app_state.config_sql_read_limit_default), ("page", "int", 0, None, 1), ("status", "int", 0, [1, 2, 3, 4], None), ("customer_name", "str", 0, None, None)])
    values, where = [], []
    if oq.get("status"):
        values.append(oq["status"])
        where.append(f"q.status=${len(values)}")
    if oq.get("customer_name"):
        values.append(f"%{oq['customer_name']}%")
        where.append(f"q.customer_name ilike ${len(values)}")
    where_sql = f"where {' and '.join(where)}" if where else ""
    values.extend([oq["limit"] + 1, (oq["page"] - 1) * oq["limit"]])
    sql = f"""
        select q.*, r.mode, r.origin, r.destination, r.carrier, r.commodity, r.charge_unit, r.currency, r.min_sell_rate, r.origin_charges, r.destination_charges, r.transit_days, r.remarks as rate_remarks, q.quoted_rate + coalesce(r.origin_charges, 0) + coalesce(r.destination_charges, 0) as final_quote_amount
        from quotations q
        left join rates r on r.id = q.rate_id
        {where_sql}
        order by q.id desc
        limit ${len(values)-1} offset ${len(values)}
    """
    async with app_state.client_postgres_read_fallback.acquire() as conn:
        rows = await conn.fetch(sql, *values)
    ol = [dict(row) for row in rows]
    return {"status": 1, "message": {"obj_list": ol[:oq["limit"]], "has_next_page": len(ol) > oq["limit"]}}
