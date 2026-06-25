from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import asyncio
import csv
import io
import json
import re
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
                current_setting('work_mem') AS work_mem,
                current_setting('maintenance_work_mem') AS maintenance_work_mem,
                current_setting('effective_cache_size', true) AS effective_cache_size,
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
                COUNT(*) FILTER (WHERE state = 'idle in transaction')::int AS idle_transaction_count,
                COUNT(*) FILTER (WHERE wait_event IS NOT NULL)::int AS waiting_connection_count,
                COUNT(*) FILTER (WHERE wait_event_type = 'Lock')::int AS lock_wait_connection_count,
                COUNT(*) FILTER (WHERE state = 'active' AND query_start < now() - interval '5 minutes')::int AS active_over_5min_count,
                COUNT(*) FILTER (WHERE state = 'idle in transaction' AND xact_start < now() - interval '5 minutes')::int AS idle_transaction_over_5min_count,
                COALESCE(EXTRACT(EPOCH FROM MAX(now() - query_start) FILTER (WHERE state = 'active' AND query_start IS NOT NULL))::bigint, 0) AS max_active_query_age_seconds,
                COALESCE(EXTRACT(EPOCH FROM MAX(now() - xact_start) FILTER (WHERE state = 'idle in transaction' AND xact_start IS NOT NULL))::bigint, 0) AS max_idle_transaction_age_seconds
            FROM pg_stat_activity
            WHERE datname = current_database();
        """))
        stats_info = dict(await conn.fetchrow("""
            SELECT
                xact_commit,
                xact_rollback,
                deadlocks,
                temp_files,
                temp_bytes,
                pg_size_pretty(temp_bytes) AS temp_size,
                tup_returned,
                tup_fetched,
                tup_inserted,
                tup_updated,
                tup_deleted,
                blks_read,
                blks_hit,
                CASE
                    WHEN xact_commit + xact_rollback = 0 THEN NULL
                    ELSE ROUND((xact_rollback::numeric / (xact_commit + xact_rollback)) * 100, 2)::float8
                END AS rollback_ratio_pct,
                CASE
                    WHEN blks_hit + blks_read = 0 THEN NULL
                    ELSE ROUND((blks_hit::numeric / (blks_hit + blks_read)) * 100, 2)::float8
                END AS cache_hit_ratio_pct
            FROM pg_stat_database
            WHERE datname = current_database();
        """))
        stats_view_info = dict(await conn.fetchrow("SELECT to_regclass('pg_catalog.pg_stat_checkpointer') IS NOT NULL AS has_checkpointer_stats;"))
        if stats_view_info["has_checkpointer_stats"]:
            bgwriter_info = dict(await conn.fetchrow("""
                SELECT
                    cp.num_timed AS checkpoints_timed,
                    cp.num_requested AS checkpoints_req,
                    cp.write_time AS checkpoint_write_time,
                    cp.sync_time AS checkpoint_sync_time,
                    cp.buffers_written AS buffers_checkpoint,
                    bg.buffers_clean,
                    bg.maxwritten_clean,
                    NULL::bigint AS buffers_backend,
                    NULL::bigint AS buffers_backend_fsync,
                    bg.buffers_alloc,
                    cp.stats_reset::text AS bgwriter_stats_reset_at
                FROM pg_stat_checkpointer cp
                CROSS JOIN pg_stat_bgwriter bg;
            """))
        else:
            bgwriter_info = dict(await conn.fetchrow("""
                SELECT
                    checkpoints_timed,
                    checkpoints_req,
                    checkpoint_write_time,
                    checkpoint_sync_time,
                    buffers_checkpoint,
                    buffers_clean,
                    maxwritten_clean,
                    buffers_backend,
                    buffers_backend_fsync,
                    buffers_alloc,
                    stats_reset::text AS bgwriter_stats_reset_at
                FROM pg_stat_bgwriter;
            """))
        table_stats_info = dict(await conn.fetchrow("""
            SELECT
                COALESCE(SUM(n_live_tup), 0)::bigint AS live_tuple_estimate,
                COALESCE(SUM(n_dead_tup), 0)::bigint AS dead_tuple_estimate,
                CASE
                    WHEN SUM(n_live_tup + n_dead_tup) = 0 THEN NULL
                    ELSE ROUND((SUM(n_dead_tup)::numeric / SUM(n_live_tup + n_dead_tup)) * 100, 2)::float8
                END AS dead_tuple_pct,
                COALESCE(SUM(seq_scan), 0)::bigint AS seq_scan_count,
                COALESCE(SUM(idx_scan), 0)::bigint AS idx_scan_count,
                CASE
                    WHEN SUM(seq_scan + idx_scan) = 0 THEN NULL
                    ELSE ROUND((SUM(seq_scan)::numeric / SUM(seq_scan + idx_scan)) * 100, 2)::float8
                END AS seq_scan_pct,
                COALESCE(SUM(vacuum_count), 0)::bigint AS manual_vacuum_count,
                COALESCE(SUM(autovacuum_count), 0)::bigint AS autovacuum_count,
                COALESCE(SUM(analyze_count), 0)::bigint AS manual_analyze_count,
                COALESCE(SUM(autoanalyze_count), 0)::bigint AS autoanalyze_count
            FROM pg_stat_user_tables;
        """))
        table_io_info = dict(await conn.fetchrow("""
            SELECT
                COALESCE(SUM(heap_blks_read), 0)::bigint AS table_heap_blks_read,
                COALESCE(SUM(heap_blks_hit), 0)::bigint AS table_heap_blks_hit,
                COALESCE(SUM(idx_blks_read), 0)::bigint AS index_blks_read,
                COALESCE(SUM(idx_blks_hit), 0)::bigint AS index_blks_hit,
                CASE
                    WHEN SUM(heap_blks_read + heap_blks_hit) = 0 THEN NULL
                    ELSE ROUND((SUM(heap_blks_hit)::numeric / SUM(heap_blks_read + heap_blks_hit)) * 100, 2)::float8
                END AS table_cache_hit_ratio_pct,
                CASE
                    WHEN SUM(idx_blks_read + idx_blks_hit) = 0 THEN NULL
                    ELSE ROUND((SUM(idx_blks_hit)::numeric / SUM(idx_blks_read + idx_blks_hit)) * 100, 2)::float8
                END AS index_cache_hit_ratio_pct
            FROM pg_statio_user_tables;
        """))
        top_dead_tuple_relations = [dict(row) for row in await conn.fetch("""
            SELECT
                schemaname AS schema_name,
                relname AS relation_name,
                n_live_tup AS live_tuple_estimate,
                n_dead_tup AS dead_tuple_estimate,
                CASE
                    WHEN n_live_tup + n_dead_tup = 0 THEN NULL
                    ELSE ROUND((n_dead_tup::numeric / (n_live_tup + n_dead_tup)) * 100, 2)::float8
                END AS dead_tuple_pct,
                last_autovacuum::text AS last_autovacuum_at,
                last_autoanalyze::text AS last_autoanalyze_at
            FROM pg_stat_user_tables
            WHERE n_dead_tup > 0
            ORDER BY n_dead_tup DESC
            LIMIT 5;
        """)]
        extensions = [dict(row) for row in await conn.fetch("""
            SELECT
                e.extname AS name,
                e.extversion AS version,
                n.nspname AS schema_name
            FROM pg_extension e
            JOIN pg_namespace n ON n.oid = e.extnamespace
            ORDER BY e.extname;
        """)]
    max_connections = int(database_info.get("max_connections") or 0)
    connection_count = int(activity_info.get("connection_count") or 0)
    activity_info["connection_utilization_pct"] = round((connection_count / max_connections) * 100, 2) if max_connections else None
    return {
        "status": 1,
        "message": {
            **database_info,
            **relation_counts,
            **storage_info,
            **activity_info,
            **stats_info,
            **bgwriter_info,
            **table_stats_info,
            **table_io_info,
            "extension_count": len(extensions),
            "extensions": extensions,
            "largest_relations": largest_relations,
            "top_dead_tuple_relations": top_dead_tuple_relations,
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

@router.post("/postgres/query-runner-read")
async def func_api_postgres_query_runner_read(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_external: raise Exception("external postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    sql = str(ob["sql"] or "").strip().rstrip(";").strip()
    if not sql: raise Exception("SQL is required")
    if ";" in sql: raise Exception("Only one SQL statement is allowed")
    if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("Only SELECT/WITH queries are supported")
    timeout_sec = 30
    async with app_state.client_postgres_external.acquire() as conn:
        async with conn.transaction(readonly=True):
            await conn.execute(f"SET LOCAL statement_timeout = '{timeout_sec * 1000}ms'")
            stmt = await conn.prepare(f"SELECT * FROM ({sql}) AS postgres_query LIMIT $1")
            records = await stmt.fetch(app_state.config_query_runner_read_limit, timeout=timeout_sec)
    return {"status": 1, "message": [dict(row) for row in records]}

@router.post("/postgres/query-runner-read-export")
async def func_api_postgres_query_runner_read_export(*, request: Request):
    app_state = request.app.state
    if not app_state.client_postgres_external: raise Exception("external postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("sql", "str", 1, None, None)])
    sql = str(ob["sql"] or "").strip().rstrip(";").strip()
    if not sql: raise Exception("SQL is required")
    if ";" in sql: raise Exception("Only one SQL statement is allowed")
    if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("Only SELECT/WITH queries are supported")
    timeout_sec = 30
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
                async for record in stmt.cursor(app_state.config_query_runner_export_limit, prefetch=250, timeout=timeout_sec):
                    writer.writerow([record[column] for column in columns])
                    yield buffer.getvalue()
                    buffer.seek(0); buffer.truncate(0)
    return StreamingResponse(_iter(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=postgres_query_result.csv"})

@router.post("/postgres/query-ai")
async def func_api_postgres_query_ai(*, request: Request):
    app_state = request.app.state
    if not app_state.client_gemini: raise Exception("Gemini client not initialized")
    if not app_state.client_postgres_external: raise Exception("external postgres client not initialized")
    ob = await app_state.func_request_param_read(request=request, mode="body", strict=0, config=[("question", "str", 1, None, None)])
    question = str(ob["question"] or "").strip()
    default_limit = 10
    max_limit = app_state.config_query_runner_read_limit
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
    def func_postgres_query_ai_blocked_message(message: str) -> str:
        message = str(message or "").strip()
        if not message or re.search(r"\b(success|successfully|generated|done|created)\b", message, flags=re.IGNORECASE):
            return "Could not generate a safe SQL query. Please mention a valid object. Filters must use indexed columns."
        return message
    def func_postgres_query_ai_clean_identifier(identifier: str) -> str:
        return str(identifier or "").strip().strip('"')
    def func_postgres_query_ai_resolve_table_key(*, value: str, cache_postgres_external_schema: dict) -> str:
        value = func_postgres_query_ai_clean_identifier(value)
        if not value: return ""
        value = re.sub(r"\s*\.\s*", ".", value)
        lookup = {key.lower(): key for key in (cache_postgres_external_schema or {}).keys()}
        lookup.update({str(table.get("table_name") or key.split(".")[-1]).lower(): key for key, table in (cache_postgres_external_schema or {}).items()})
        return lookup.get(value.lower(), "")
    def func_postgres_query_ai_resolve_column_name(*, table_key: str, value: str, cache_postgres_external_schema: dict) -> str:
        value = func_postgres_query_ai_clean_identifier(value)
        if not table_key or not value: return ""
        columns = (cache_postgres_external_schema.get(table_key, {}).get("columns") or {})
        lookup = {column.lower(): column for column in columns.keys()}
        return lookup.get(value.lower(), "")
    def func_postgres_query_ai_validate_sql(*, sql: str, default_limit: int, max_limit: int, cache_postgres_external_schema: dict) -> str:
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
            table_key = func_postgres_query_ai_resolve_table_key(value=table_key, cache_postgres_external_schema=cache_postgres_external_schema) or table_key
            if table_key not in known_tables: raise Exception(f"AI generated SQL for unknown object: {table_key}")
            alias = raw_alias.strip().strip('"') if raw_alias else parts[-1]
            if alias.lower() in {"where", "join", "on", "group", "order", "limit"}: alias = parts[-1]
            alias_to_table[alias] = table_key
        where_match = re.search(r'\bwhere\b(.+?)(?:\bgroup\s+by\b|\border\s+by\b|\blimit\b|$)', sql, flags=re.IGNORECASE | re.DOTALL)
        if where_match:
            filters = re.findall(r'(?:(?:"([^"]+)"|(\w+))\s*\.\s*)?(?:"([^"]+)"|(\w+))\s*(=|<>|!=|>=|<=|>|<|\bILIKE\b|\bLIKE\b|\bIN\b|\bBETWEEN\b)', where_match.group(1), flags=re.IGNORECASE)
            for quoted_alias, plain_alias, quoted_col, plain_col, _operator in filters:
                alias = quoted_alias or plain_alias
                column = quoted_col or plain_col
                candidate_tables = [alias_to_table[alias]] if alias and alias in alias_to_table else list(alias_to_table.values())
                column_names = [(table_key, func_postgres_query_ai_resolve_column_name(table_key=table_key, value=column, cache_postgres_external_schema=cache_postgres_external_schema)) for table_key in candidate_tables]
                column_matches = [cache_postgres_external_schema[table_key]["columns"][column_name] for table_key, column_name in column_names if column_name]
                if not column_matches: raise Exception(f"AI generated filter on unknown column: {column}")
                if column_matches and not any(col.get("is_indexed") for col in column_matches): raise Exception(f"AI generated filter on non-indexed column: {column}")
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
        "2. If the request cannot be answered safely, return sql null and a short message.",
        "3. Generate only SELECT or WITH SQL.",
        "4. Use only objects and columns from the schema below.",
        f"5. If the user asks for a limit, use that LIMIT up to {max_limit}. If the user does not ask for a limit, use LIMIT {default_limit}.",
        "6. Prefer public schema objects without schema qualification when schema_name is public.",
        "7. Do not drop user intent. If the user asks for a specific value, place, customer, port, country, status, date, or other filter, include that filter.",
        "8. WHERE filters must use indexed columns. If the request requires filtering on a non-indexed column or no matching indexed column is clear, return sql null and ask admin to create an index or mention the indexed column.",
        "9. For text prefix search, use ILIKE 'value%'. Avoid broad contains search unless the column has a gin index.",
        "10. Limit-only SELECT from an explicitly named object is allowed and does not need an indexed filter.",
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
    if not data.get("sql"):
        return {"status": 1, "message": {"sql": None, "message": func_postgres_query_ai_blocked_message(data.get("message")), "warnings": data.get("warnings") or []}}
    try:
        sql = func_postgres_query_ai_validate_sql(sql=data.get("sql"), default_limit=default_limit, max_limit=max_limit, cache_postgres_external_schema=cache_postgres_external_schema)
    except Exception as e:
        return {"status": 1, "message": {"sql": None, "message": str(e), "warnings": data.get("warnings") or []}}
    return {"status": 1, "message": {"sql": sql, "message": "SQL generated in the editor. Review before Run or Export.", "warnings": data.get("warnings") or []}}
