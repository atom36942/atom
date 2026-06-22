from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import asyncio
import csv
import io
import json
import re
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID
from google.genai import types

# router
router = APIRouter()

# api
@router.get("/postgres/database-info")
async def func_api_postgres_database_info(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_external: raise Exception("external postgres client not initialized")
    async with app_state.client_postgres_external.acquire() as conn:
        database_info = dict(await conn.fetchrow("""
            SELECT
                current_database() AS database_name,
                current_user AS current_user,
                inet_server_addr()::text AS server_address,
                inet_server_port() AS server_port,
                current_setting('server_version') AS server_version,
                current_setting('TimeZone') AS timezone,
                current_setting('max_connections') AS max_connections,
                current_setting('shared_buffers') AS shared_buffers,
                pg_postmaster_start_time()::text AS server_started_at,
                pg_get_userbyid(d.datdba) AS database_owner,
                pg_encoding_to_char(d.encoding) AS database_encoding,
                d.datcollate AS database_collation,
                d.datctype AS database_ctype,
                d.datallowconn AS allow_connections,
                d.datconnlimit AS connection_limit,
                pg_database_size(current_database()) AS database_size_bytes,
                pg_size_pretty(pg_database_size(current_database())) AS database_size,
                now()::text AS checked_at
            FROM pg_database d
            WHERE d.datname = current_database();
        """))
        relation_counts = dict(await conn.fetchrow("""
            WITH user_schemas AS (
                SELECT oid
                FROM pg_namespace
                WHERE nspname NOT IN ('pg_catalog', 'information_schema')
                  AND nspname NOT LIKE 'pg_%'
            ),
            user_relations AS (
                SELECT c.relkind
                FROM pg_class c
                JOIN user_schemas n ON n.oid = c.relnamespace
            )
            SELECT
                (SELECT COUNT(*)::int FROM user_schemas) AS schema_count,
                COUNT(*) FILTER (WHERE relkind IN ('r', 'p'))::int AS table_count,
                COUNT(*) FILTER (WHERE relkind = 'v')::int AS view_count,
                COUNT(*) FILTER (WHERE relkind = 'm')::int AS materialized_view_count,
                COUNT(*) FILTER (WHERE relkind = 'i')::int AS index_count
            FROM user_relations;
        """))
        largest_relations = [dict(row) for row in await conn.fetch("""
            SELECT
                n.nspname AS schema_name,
                c.relname AS relation_name,
                CASE c.relkind
                    WHEN 'r' THEN 'table'
                    WHEN 'p' THEN 'partitioned_table'
                    WHEN 'm' THEN 'materialized_view'
                    WHEN 'i' THEN 'index'
                    WHEN 'v' THEN 'view'
                    ELSE c.relkind::text
                END AS relation_type,
                pg_total_relation_size(c.oid) AS total_size_bytes,
                pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
              AND n.nspname NOT LIKE 'pg_%'
              AND c.relkind IN ('r', 'p', 'm', 'i')
            ORDER BY pg_total_relation_size(c.oid) DESC
            LIMIT 10;
        """)]
        storage_info = dict(await conn.fetchrow("""
            SELECT
                pg_size_pretty(COALESCE(SUM(pg_table_size(c.oid)), 0)::bigint) AS table_size,
                pg_size_pretty(COALESCE(SUM(pg_indexes_size(c.oid)), 0)::bigint) AS index_size,
                pg_size_pretty(COALESCE(SUM(pg_total_relation_size(c.oid)), 0)::bigint) AS relation_total_size
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
              AND n.nspname NOT LIKE 'pg_%'
              AND c.relkind IN ('r', 'p', 'm');
        """))
        activity_info = dict(await conn.fetchrow("""
            SELECT
                COUNT(*)::int AS connection_count,
                COUNT(*) FILTER (WHERE state = 'active')::int AS active_connection_count,
                COUNT(*) FILTER (WHERE state = 'idle')::int AS idle_connection_count,
                COUNT(*) FILTER (WHERE state = 'idle in transaction')::int AS idle_transaction_count
            FROM pg_stat_activity
            WHERE datname = current_database();
        """))
        stats_info = dict(await conn.fetchrow("""
            SELECT
                xact_commit,
                xact_rollback,
                deadlocks,
                temp_files,
                pg_size_pretty(temp_bytes) AS temp_size,
                tup_returned,
                tup_fetched,
                tup_inserted,
                tup_updated,
                tup_deleted,
                CASE
                    WHEN blks_hit + blks_read = 0 THEN NULL
                    ELSE ROUND((blks_hit::numeric / (blks_hit + blks_read)) * 100, 2)::float8
                END AS cache_hit_ratio_pct
            FROM pg_stat_database
            WHERE datname = current_database();
        """))
        extensions = [dict(row) for row in await conn.fetch("""
            SELECT
                e.extname AS name,
                e.extversion AS version,
                n.nspname AS schema_name
            FROM pg_extension e
            JOIN pg_namespace n ON n.oid = e.extnamespace
            ORDER BY e.extname;
        """)]
    return {
        "status": 1,
        "message": {
            **database_info,
            **relation_counts,
            **storage_info,
            **activity_info,
            **stats_info,
            "extension_count": len(extensions),
            "extensions": extensions,
            "largest_relations": largest_relations,
        },
    }

@router.get("/postgres/schema")
async def func_api_postgres_schema(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_external: raise Exception("external postgres client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, 5000), ("page", "int", 0, None, 1)])
    limit = max(1, min(oq["limit"], 10000))
    async with app_state.client_postgres_external.acquire() as conn:
        offset = (oq["page"] - 1) * limit
        rows = [dict(row) for row in await conn.fetch("""
            WITH user_schemas AS (
                SELECT oid, nspname
                FROM pg_namespace
                WHERE nspname NOT IN ('pg_catalog', 'information_schema')
                  AND nspname NOT LIKE 'pg_%'
            ),
            column_base AS (
                SELECT
                    n.nspname AS schema_name,
                    c.relname AS table_name,
                    CASE c.relkind
                        WHEN 'r' THEN 'table'
                        WHEN 'p' THEN 'partitioned_table'
                        WHEN 'v' THEN 'view'
                        WHEN 'm' THEN 'materialized_view'
                        WHEN 'f' THEN 'foreign_table'
                        ELSE c.relkind::text
                    END AS relation_type,
                    c.oid AS relation_oid,
                    a.attnum AS column_number,
                    a.attname AS column_name,
                    format_type(a.atttypid, a.atttypmod) AS data_type,
                    NOT a.attnotnull AS is_nullable,
                    pg_get_expr(d.adbin, d.adrelid) AS column_default
                FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                JOIN user_schemas n ON n.oid = c.relnamespace
                LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
                WHERE a.attnum > 0
                  AND NOT a.attisdropped
                  AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
            ),
            constraints_by_column AS (
                SELECT
                    con.conrelid AS relation_oid,
                    attnum AS column_number,
                    BOOL_OR(con.contype = 'p') AS is_primary,
                    BOOL_OR(con.contype = 'u') AS is_unique_constraint
                FROM pg_constraint con
                CROSS JOIN LATERAL UNNEST(con.conkey) AS attnum
                WHERE con.contype IN ('p', 'u')
                GROUP BY con.conrelid, attnum
            ),
            index_columns AS (
                SELECT
                    i.indrelid AS relation_oid,
                    key_att.attnum AS column_number,
                    am.amname AS index_method,
                    idx.relname AS index_name,
                    i.indisunique AS is_unique_index
                FROM pg_index i
                JOIN pg_class idx ON idx.oid = i.indexrelid
                JOIN pg_am am ON am.oid = idx.relam
                CROSS JOIN LATERAL UNNEST(i.indkey) AS key_att(attnum)
                WHERE key_att.attnum > 0
            ),
            indexes_by_column AS (
                SELECT
                    relation_oid,
                    column_number,
                    BOOL_OR(is_unique_index) AS is_unique_index,
                    COUNT(*)::int AS index_count,
                    ARRAY_REMOVE(ARRAY_AGG(index_name ORDER BY index_name) FILTER (WHERE index_method = 'btree'), NULL) AS btree_indexes,
                    ARRAY_REMOVE(ARRAY_AGG(index_name ORDER BY index_name) FILTER (WHERE index_method = 'gin'), NULL) AS gin_indexes,
                    ARRAY_REMOVE(ARRAY_AGG(index_name ORDER BY index_name) FILTER (WHERE index_method = 'gist'), NULL) AS gist_indexes,
                    ARRAY_REMOVE(ARRAY_AGG(index_name ORDER BY index_name) FILTER (WHERE index_method = 'brin'), NULL) AS brin_indexes,
                    ARRAY_REMOVE(ARRAY_AGG(index_name ORDER BY index_name) FILTER (WHERE index_method = 'hash'), NULL) AS hash_indexes,
                    ARRAY_REMOVE(ARRAY_AGG(index_name || ' (' || index_method || ')' ORDER BY index_name) FILTER (WHERE index_method NOT IN ('btree', 'gin', 'gist', 'brin', 'hash')), NULL) AS other_indexes
                FROM index_columns
                GROUP BY relation_oid, column_number
            )
            SELECT
                cb.schema_name,
                cb.table_name,
                cb.relation_type,
                cb.column_name,
                cb.data_type,
                cb.is_nullable,
                cb.column_default,
                COALESCE(cbc.is_primary, FALSE) AS is_primary,
                COALESCE(cbc.is_unique_constraint, FALSE) AS is_unique_constraint,
                COALESCE(ibc.is_unique_index, FALSE) AS is_unique_index,
                COALESCE(ibc.index_count, 0) AS index_count,
                COALESCE(ibc.btree_indexes, ARRAY[]::text[]) AS btree_indexes,
                COALESCE(ibc.gin_indexes, ARRAY[]::text[]) AS gin_indexes,
                COALESCE(ibc.gist_indexes, ARRAY[]::text[]) AS gist_indexes,
                COALESCE(ibc.brin_indexes, ARRAY[]::text[]) AS brin_indexes,
                COALESCE(ibc.hash_indexes, ARRAY[]::text[]) AS hash_indexes,
                COALESCE(ibc.other_indexes, ARRAY[]::text[]) AS other_indexes
            FROM column_base cb
            LEFT JOIN constraints_by_column cbc
              ON cbc.relation_oid = cb.relation_oid AND cbc.column_number = cb.column_number
            LEFT JOIN indexes_by_column ibc
              ON ibc.relation_oid = cb.relation_oid AND ibc.column_number = cb.column_number
            ORDER BY cb.schema_name, cb.table_name, cb.column_number
            LIMIT $1 OFFSET $2;
        """, limit + 1, offset)]
    return {"status": 1, "message": {"obj_list": rows[:limit], "has_next_page": len(rows) > limit}}

@router.post("/postgres/query-runner-write")
async def func_api_postgres_query_runner_write(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_external: raise Exception("external postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    sql = str(ob["sql"] or "").strip().rstrip(";").strip()
    if not sql: raise Exception("SQL is required")
    if ";" in sql: raise Exception("Only one SQL statement is allowed")
    ql = sql.lower().lstrip("(").strip()
    if ql.startswith(("select", "with", "explain", "show", "describe")): raise Exception("read SQL must use /postgres/query-runner-read")
    if "returning" in ql: raise Exception("RETURNING is not allowed in write mode")
    timeout_sec = 30
    async with app_state.client_postgres_external.acquire() as conn:
        async with conn.transaction():
            await conn.execute(f"SET LOCAL statement_timeout = '{timeout_sec * 1000}ms'")
            result = await conn.execute(sql, timeout=timeout_sec)
    return {"status": 1, "message": {"mode": "write", "result": result}}

@router.post("/postgres/query-runner-read")
async def func_api_postgres_query_runner_read(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_external: raise Exception("external postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    sql = str(ob["sql"] or "").strip().rstrip(";").strip()
    if not sql: raise Exception("SQL is required")
    if ";" in sql: raise Exception("Only one SQL statement is allowed")
    if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("Only SELECT/WITH queries are supported")
    limit = app_state.config_query_runner_read_limit
    timeout_sec = 30
    def serialize(value):
        if value is None: return None
        if isinstance(value, (list, tuple)): return [serialize(item) for item in value]
        if isinstance(value, dict): return {key: serialize(item) for key, item in value.items()}
        if isinstance(value, (datetime, date, time)): return value.isoformat()
        if isinstance(value, Decimal): return float(value)
        if isinstance(value, UUID): return str(value)
        if isinstance(value, bytes): return value.hex()
        if isinstance(value, (str, int, float, bool)): return value
        return str(value)
    async with app_state.client_postgres_external.acquire() as conn:
        async with conn.transaction(readonly=True):
            await conn.execute(f"SET LOCAL statement_timeout = '{timeout_sec * 1000}ms'")
            stmt = await conn.prepare(f"SELECT * FROM ({sql}) AS postgres_query LIMIT $1")
            columns = [attr.name for attr in stmt.get_attributes()]
            records = await stmt.fetch(limit, timeout=timeout_sec)
    return {
        "status": 1,
        "message": {
            "columns": columns,
            "rows": [{key: serialize(value) for key, value in dict(row).items()} for row in records],
            "limit": limit,
            "max_limit": limit,
            "row_count": len(records),
            "is_limited": len(records) >= limit,
        },
    }

@router.post("/postgres/query-runner-read-export")
async def func_api_postgres_query_runner_read_export(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_external: raise Exception("external postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    sql = str(ob["sql"] or "").strip().rstrip(";").strip()
    if not sql: raise Exception("SQL is required")
    if ";" in sql: raise Exception("Only one SQL statement is allowed")
    if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("Only SELECT/WITH queries are supported")
    limit = app_state.config_query_runner_export_limit
    timeout_sec = 30
    def csv_value(value):
        if value is None: return ""
        if isinstance(value, (datetime, date, time)): return value.isoformat()
        if isinstance(value, Decimal): return str(value)
        if isinstance(value, UUID): return str(value)
        if isinstance(value, bytes): return value.hex()
        if isinstance(value, (list, tuple, dict)): return str(value)
        return str(value)
    async def _iter():
        async with app_state.client_postgres_external.acquire() as conn:
            async with conn.transaction(readonly=True):
                await conn.execute(f"SET LOCAL statement_timeout = '{timeout_sec * 1000}ms'")
                stmt = await conn.prepare(f"SELECT * FROM ({sql}) AS postgres_query LIMIT $1")
                columns = [attr.name for attr in stmt.get_attributes()]
                buffer = io.StringIO()
                writer = csv.writer(buffer)
                writer.writerow(columns)
                yield buffer.getvalue()
                buffer.seek(0); buffer.truncate(0)
                async for record in stmt.cursor(limit, prefetch=250, timeout=timeout_sec):
                    writer.writerow([csv_value(record[column]) for column in columns])
                    yield buffer.getvalue()
                    buffer.seek(0); buffer.truncate(0)
    return StreamingResponse(
        _iter(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=postgres_query_result.csv"},
    )

@router.post("/postgres/query-ai")
async def func_api_postgres_query_ai(*, request: Request):
    app_state = request.app.state
    if not app_state.client_gemini: raise Exception("Gemini client not initialized")
    if not app_state.client_postgres_external: raise Exception("external postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("question", "str", 1, None, None)])
    question = str(ob["question"] or "").strip()
    default_limit = 10
    max_limit = app_state.config_query_runner_read_limit
    POSTGRES_QUERY_AI_STOP_WORDS = {
        "a", "about", "all", "also", "an", "and", "any", "as", "by", "data", "for", "from", "get", "give", "in", "last", "latest", "limit",
        "list", "me", "of", "on", "or", "record", "records", "recent", "row", "rows", "select", "show", "shipment", "shipments", "table",
        "the", "to", "top", "with",
    }
    def func_postgres_query_ai_schema_prompt(cache_postgres_external_schema: dict) -> list:
        output = []
        for table_key, table in sorted((cache_postgres_external_schema or {}).items()):
            columns = []
            for column_name, column in sorted(table.get("columns", {}).items()):
                columns.append({
                    "name": column_name,
                    "data_type": column.get("data_type"),
                    "is_indexed": bool(column.get("is_indexed")),
                    "index_methods": column.get("index_methods") or [],
                    "is_primary": bool(column.get("is_primary")),
                    "is_unique": bool(column.get("is_unique")),
                })
            output.append({"table": table_key, "relation_type": table.get("relation_type"), "columns": columns})
        return output

    def func_postgres_query_ai_schema_terms(cache_postgres_external_schema: dict) -> set:
        terms = set()
        for table_key, table in (cache_postgres_external_schema or {}).items():
            for item in [table_key, table.get("schema_name"), table.get("table_name"), table.get("relation_type")]:
                terms.update(re.findall(r"[a-z0-9]+", str(item or "").lower()))
            for column_name in (table.get("columns") or {}).keys():
                terms.update(re.findall(r"[a-z0-9]+", str(column_name or "").lower()))
        return terms

    def func_postgres_query_ai_question_value_terms(*, question: str, stop_words: set, cache_postgres_external_schema: dict) -> list:
        schema_terms = func_postgres_query_ai_schema_terms(cache_postgres_external_schema)
        terms = []
        for word in re.findall(r"[a-z0-9]+", str(question or "").lower()):
            if len(word) < 3 or word.isdigit(): continue
            if word in stop_words or word in schema_terms: continue
            if word not in terms: terms.append(word)
        return terms

    def func_postgres_query_ai_validate_sql(*, question: str, sql: str, default_limit: int, max_limit: int, stop_words: set, cache_postgres_external_schema: dict) -> str:
        sql = str(sql or "").strip().rstrip(";").strip()
        if not sql: raise Exception("AI did not generate SQL.")
        if ";" in sql: raise Exception("AI generated multiple SQL statements.")
        if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("AI generated non-read SQL.")
        known_tables = set((cache_postgres_external_schema or {}).keys())
        table_matches = re.findall(r'\b(?:from|join)\s+((?:"[^"]+"|\w+)(?:\s*\.\s*(?:"[^"]+"|\w+))?)(?:\s+(?:as\s+)?("[^"]+"|\w+))?', sql, flags=re.IGNORECASE)
        alias_to_table = {}
        for raw_table, raw_alias in table_matches:
            parts = [part.strip().strip('"') for part in raw_table.split(".")]
            table_key = ".".join(parts) if len(parts) > 1 else f"public.{parts[0]}"
            if table_key not in known_tables: raise Exception(f"AI generated SQL for unknown object: {table_key}")
            alias = raw_alias.strip().strip('"') if raw_alias else parts[-1]
            if alias.lower() not in {"where", "join", "on", "group", "order", "limit"}: alias_to_table[alias] = table_key
        where_match = re.search(r'\bwhere\b(.+?)(?:\bgroup\s+by\b|\border\s+by\b|\blimit\b|$)', sql, flags=re.IGNORECASE | re.DOTALL)
        if where_match:
            filters = re.findall(r'(?:(?:"([^"]+)"|(\w+))\s*\.\s*)?(?:"([^"]+)"|(\w+))\s*(=|<>|!=|>=|<=|>|<|\bILIKE\b|\bLIKE\b|\bIN\b|\bBETWEEN\b)', where_match.group(1), flags=re.IGNORECASE)
            for quoted_alias, plain_alias, quoted_col, plain_col, _operator in filters:
                alias = quoted_alias or plain_alias
                column = quoted_col or plain_col
                candidate_tables = [alias_to_table[alias]] if alias and alias in alias_to_table else list(alias_to_table.values())
                column_matches = [cache_postgres_external_schema[table_key]["columns"].get(column) for table_key in candidate_tables if column in cache_postgres_external_schema.get(table_key, {}).get("columns", {})]
                if column_matches and not any(col.get("is_indexed") for col in column_matches): raise Exception(f"AI generated filter on non-indexed column: {column}")
        value_terms = func_postgres_query_ai_question_value_terms(question=question, stop_words=stop_words, cache_postgres_external_schema=cache_postgres_external_schema)
        if value_terms:
            sql_lower = sql.lower()
            missing_terms = [term for term in value_terms if term not in sql_lower]
            if missing_terms: raise Exception(f"AI skipped requested filter value: {', '.join(missing_terms[:3])}. Please ask with an indexed column name, or ask admin to create the required index.")
            if not re.search(r"\b(where|having)\b", sql, flags=re.IGNORECASE): raise Exception("AI skipped the requested filter. Please ask with an indexed column name.")
        limit_match = re.search(r'\blimit\s+(\d+)\s*$', sql, flags=re.IGNORECASE)
        if limit_match:
            limit = max(1, min(int(limit_match.group(1)), max_limit))
            sql = re.sub(r'\blimit\s+\d+\s*$', f"LIMIT {limit}", sql, flags=re.IGNORECASE)
        else:
            sql = f"{sql}\nLIMIT {default_limit}"
        return f"{sql.rstrip(';')};"

    cache_postgres_external_schema = getattr(app_state, "cache_postgres_external_schema", {}) or {}
    if not cache_postgres_external_schema:
        app_state.cache_postgres_external_schema = await app_state.func_postgres_ai_schema_read(client_postgres=app_state.client_postgres_external)
        cache_postgres_external_schema = app_state.cache_postgres_external_schema
    prompt_schema = func_postgres_query_ai_schema_prompt(cache_postgres_external_schema)
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "status": {"type": "STRING"},
            "sql": {"type": "STRING", "nullable": True},
            "message": {"type": "STRING"},
            "warnings": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
    }
    prompt = "\n".join([
        "You generate safe PostgreSQL SELECT SQL for an internal read-only query runner.",
        "",
        "Rules:",
        "1. Return JSON only in the requested schema.",
        '2. If the request cannot be answered safely, return status "blocked", sql null, and a short message.',
        "3. Generate only SELECT or WITH SQL.",
        "4. Use only objects and columns from the schema below.",
        f"5. If the user asks for a limit, use that LIMIT up to {max_limit}. If the user does not ask for a limit, use LIMIT {default_limit}.",
        "6. Prefer public schema objects without schema qualification when schema_name is public.",
        "7. Do not drop user intent. If the user asks for a specific value, place, customer, port, country, status, date, or other filter, the SQL must include that filter.",
        "8. WHERE filters must use indexed columns. If the user's request requires filtering on a non-indexed column or no matching indexed column is clear, return blocked and ask admin to create an index or mention the indexed column.",
        "9. For text prefix search, use ILIKE 'value%'. Avoid broad contains search unless the column has a gin index.",
        "10. Never return a broad SELECT just because a safe filter is unclear. Return blocked instead.",
        "11. Do not use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, COPY, or multiple statements.",
        "",
        "User question:",
        question,
        "",
        "Schema:",
        json.dumps(prompt_schema, separators=(",", ":")),
    ])
    response = await asyncio.to_thread(
        app_state.client_gemini.models.generate_content,
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=response_schema, temperature=0.1),
    )
    data = json.loads(response.text or "{}")
    status = str(data.get("status") or "").lower()
    if status != "ok":
        return {"status": 1, "message": {"status": "blocked", "sql": None, "message": data.get("message") or "Could not generate a safe indexed query.", "warnings": data.get("warnings") or []}}
    try:
        sql = func_postgres_query_ai_validate_sql(question=question, sql=data.get("sql"), default_limit=default_limit, max_limit=max_limit, stop_words=POSTGRES_QUERY_AI_STOP_WORDS, cache_postgres_external_schema=cache_postgres_external_schema)
    except Exception as e:
        return {"status": 1, "message": {"status": "blocked", "sql": None, "message": str(e), "warnings": data.get("warnings") or []}}
    return {"status": 1, "message": {"status": "ok", "sql": sql, "message": "SQL generated in the editor. Review before Run or Export.", "warnings": data.get("warnings") or []}}
