from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import csv
import io
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

# router
router = APIRouter()

# api
@router.get("/pgscope/database-info")
async def func_api_pgscope_database_info(*, request: Request):
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

@router.get("/pgscope/schema")
async def func_api_pgscope_schema(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_external: raise Exception("external postgres client not initialized")
    oq = await app_state.func_request_param_read(request=request, mode="query", strict=0, config=[("limit", "int", 0, None, 5000), ("page", "int", 0, None, 1)])
    limit = max(1, min(oq["limit"], 10000))
    async with app_state.client_postgres_external.acquire() as conn:
        summary = dict(await conn.fetchrow("""
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
                    a.attnum AS column_number
                FROM pg_attribute a
                JOIN pg_class c ON c.oid = a.attrelid
                JOIN user_schemas n ON n.oid = c.relnamespace
                WHERE a.attnum > 0
                  AND NOT a.attisdropped
                  AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
            ),
            relation_base AS (
                SELECT DISTINCT schema_name, table_name, relation_type
                FROM column_base
            ),
            index_columns AS (
                SELECT DISTINCT
                    i.indrelid AS relation_oid,
                    key_att.attnum AS column_number,
                    idx.relname AS index_name
                FROM pg_index i
                JOIN pg_class idx ON idx.oid = i.indexrelid
                CROSS JOIN LATERAL UNNEST(i.indkey) AS key_att(attnum)
                WHERE key_att.attnum > 0
            )
            SELECT
                COUNT(DISTINCT (cb.relation_oid, cb.column_number))::int AS column_count,
                COUNT(DISTINCT (cb.relation_oid, cb.column_number)) FILTER (WHERE ic.index_name IS NOT NULL)::int AS indexed_column_count,
                COUNT(DISTINCT ic.index_name)::int AS index_count,
                (SELECT COUNT(*)::int FROM relation_base WHERE relation_type IN ('table', 'partitioned_table', 'foreign_table')) AS table_count,
                (SELECT COUNT(*)::int FROM relation_base WHERE relation_type = 'view') AS view_count,
                (SELECT COUNT(*)::int FROM relation_base WHERE relation_type = 'materialized_view') AS materialized_view_count
            FROM column_base cb
            LEFT JOIN index_columns ic ON ic.relation_oid = cb.relation_oid AND ic.column_number = cb.column_number;
        """))
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
        columns = rows[:limit]
        has_next_page = len(rows) > limit
    return {
        "status": 1,
        "message": {
            **summary,
            "has_next_page": has_next_page,
            "pagination": {
                "page": oq["page"],
                "limit": limit,
                "max_limit": 10000,
                "total_count": int(summary.get("column_count") or 0),
                "has_prev_page": oq["page"] > 1,
                "has_next_page": has_next_page,
                "returned_count": len(columns),
            },
            "columns": columns,
        },
    }

@router.post("/pgscope/query-runner")
async def func_api_pgscope_query_runner(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_external: raise Exception("external postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    sql = str(ob["sql"] or "").strip().rstrip(";").strip()
    if not sql: raise Exception("SQL is required")
    if ";" in sql: raise Exception("Only one SQL statement is allowed")
    ql = sql.lower().lstrip("(").strip()
    limit = 5000
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
    def query_output(columns, records):
        return {"status": 1, "message": {"mode": "query", "columns": columns, "rows": [{key: serialize(value) for key, value in dict(row).items()} for row in records], "limit": limit, "max_limit": limit, "row_count": len(records), "is_limited": len(records) >= limit}}
    async with app_state.client_postgres_external.acquire() as conn:
        async with conn.transaction():
            await conn.execute(f"SET LOCAL statement_timeout = '{timeout_sec * 1000}ms'")
            if ql.startswith(("select", "with")):
                stmt = await conn.prepare(f"SELECT * FROM ({sql}) AS pgscope_query LIMIT $1")
                columns = [attr.name for attr in stmt.get_attributes()]
                records = await stmt.fetch(limit, timeout=timeout_sec)
                return query_output(columns, records)
            if not (ql.startswith(("explain", "show", "describe")) or "returning" in ql):
                result = await conn.execute(sql, timeout=timeout_sec)
                return {"status": 1, "message": {"mode": "execute", "result": result}}
            stmt = await conn.prepare(sql)
            columns = [attr.name for attr in stmt.get_attributes()]
            records = []
            async for record in stmt.cursor(prefetch=250, timeout=timeout_sec):
                records.append(record)
                if len(records) >= limit: break
            return query_output(columns, records)

@router.post("/pgscope/query-runner-read")
async def func_api_pgscope_query_runner_read(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_external: raise Exception("external postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    sql = str(ob["sql"] or "").strip().rstrip(";").strip()
    if not sql: raise Exception("SQL is required")
    if ";" in sql: raise Exception("Only one SQL statement is allowed")
    if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("Only SELECT/WITH queries are supported")
    limit = 5000
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
            stmt = await conn.prepare(f"SELECT * FROM ({sql}) AS pgscope_query LIMIT $1")
            columns = [attr.name for attr in stmt.get_attributes()]
            records = await stmt.fetch(limit, timeout=timeout_sec)
    return {
        "status": 1,
        "message": {
            "columns": columns,
            "rows": [{key: serialize(value) for key, value in dict(row).items()} for row in records],
            "limit": limit,
            "max_limit": 5000,
            "row_count": len(records),
            "is_limited": len(records) >= limit,
        },
    }

@router.post("/pgscope/query-runner-read-export")
async def func_api_pgscope_query_runner_read_export(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_external: raise Exception("external postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    sql = str(ob["sql"] or "").strip().rstrip(";").strip()
    if not sql: raise Exception("SQL is required")
    if ";" in sql: raise Exception("Only one SQL statement is allowed")
    if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("Only SELECT/WITH queries are supported")
    limit = 5000
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
                stmt = await conn.prepare(f"SELECT * FROM ({sql}) AS pgscope_query LIMIT $1")
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
        headers={"Content-Disposition": "attachment; filename=pgscope_query_result.csv"},
    )
