"""Atom postgres metadata functions."""

async def func_postgres_info_read(*, client_postgres: any) -> dict:
    """Read comprehensive PostgreSQL database statistics, storage, activity, and schema information."""
    async with client_postgres.acquire() as conn:
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
    return {**database_info, **relation_counts, **storage_info, **activity_info, **stats_info, **bgwriter_info, **table_stats_info, **table_io_info, "extension_count": len(extensions), "extensions": extensions, "largest_relations": largest_relations, "top_dead_tuple_relations": top_dead_tuple_relations}

async def func_postgres_schema_read(*, client_postgres: any, mode: str = "table") -> dict:
    """Read PostgreSQL schema with relation and per-column index info."""
    sql = """
        WITH user_schemas AS (
            SELECT oid, nspname
            FROM pg_namespace
            WHERE nspname NOT IN ('pg_catalog', 'information_schema')
              AND nspname NOT LIKE 'pg_%'
              AND nspname = 'public'
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
              AND i.indisvalid
              AND i.indisready
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
            cb.column_number,
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
        ORDER BY cb.schema_name, cb.table_name, cb.column_number;
    """
    async with client_postgres.acquire() as conn:
        records = await conn.fetch(sql)
    rows = [dict(r) for r in records]
    for row in rows:
        for key in ("btree_indexes", "gin_indexes", "gist_indexes", "brin_indexes", "hash_indexes", "other_indexes"):
            row[key] = list(row.get(key) or [])
    if mode == "rows": return rows
    schema = {}
    for r in rows:
        index_names = []
        for key in ("btree_indexes", "gin_indexes", "gist_indexes", "brin_indexes", "hash_indexes", "other_indexes"):
            index_names.extend(r[key])
        schema.setdefault(r["table_name"], {})[r["column_name"]] = {
            "schema_name": r["schema_name"],
            "table_name": r["table_name"],
            "relation_type": r["relation_type"],
            "column_number": r["column_number"],
            "column_name": r["column_name"],
            "data_type": r["data_type"],
            "datatype": r["data_type"],
            "is_nullable": "YES" if r["is_nullable"] else "NO",
            "column_default": r["column_default"],
            "default": r["column_default"],
            "is_primary": r["is_primary"],
            "is_unique_constraint": r["is_unique_constraint"],
            "is_unique_index": r["is_unique_index"],
            "is_unique": r["is_unique_constraint"] or r["is_unique_index"],
            "is_index": r["index_count"] > 0,
            "index_count": r["index_count"],
            "index_names": index_names,
            "btree_indexes": r["btree_indexes"],
            "gin_indexes": r["gin_indexes"],
            "gist_indexes": r["gist_indexes"],
            "brin_indexes": r["brin_indexes"],
            "hash_indexes": r["hash_indexes"],
            "other_indexes": r["other_indexes"],
            "btree_cnt": len(r["btree_indexes"]),
            "gin_cnt": len(r["gin_indexes"]),
            "gist_cnt": len(r["gist_indexes"]),
            "brin_cnt": len(r["brin_indexes"]),
            "hash_cnt": len(r["hash_indexes"]),
            "spgist_cnt": 0,
            "total_index_cnt": r["index_count"],
            "usable_index_cnt": r["index_count"],
            "total_idx_scans": None
        }
    return schema

async def func_postgres_schema_read_ai(*, client_postgres: any) -> dict:
    """Read compact external PostgreSQL schema/index metadata for AI SQL generation."""
    sql = """
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
                format_type(a.atttypid, a.atttypmod) AS data_type
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN user_schemas n ON n.oid = c.relnamespace
            WHERE a.attnum > 0
              AND NOT a.attisdropped
              AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
        ),
        constraints_by_column AS (
            SELECT
                con.conrelid AS relation_oid,
                attnum AS column_number,
                BOOL_OR(con.contype = 'p') AS is_primary,
                BOOL_OR(con.contype = 'u') AS is_unique
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
                i.indisunique AS is_unique_index
            FROM pg_index i
            JOIN pg_class idx ON idx.oid = i.indexrelid
            JOIN pg_am am ON am.oid = idx.relam
            CROSS JOIN LATERAL UNNEST(i.indkey) AS key_att(attnum)
            WHERE key_att.attnum > 0
              AND i.indisvalid
              AND i.indisready
        ),
        indexes_by_column AS (
            SELECT
                relation_oid,
                column_number,
                BOOL_OR(is_unique_index) AS is_unique_index,
                ARRAY_REMOVE(ARRAY_AGG(DISTINCT index_method ORDER BY index_method), NULL) AS index_methods
            FROM index_columns
            GROUP BY relation_oid, column_number
        )
        SELECT
            cb.schema_name,
            cb.table_name,
            cb.relation_type,
            cb.column_name,
            cb.data_type,
            COALESCE(cbc.is_primary, FALSE) AS is_primary,
            COALESCE(cbc.is_unique, FALSE) AS is_unique,
            COALESCE(ibc.is_unique_index, FALSE) AS is_unique_index,
            COALESCE(ibc.index_methods, ARRAY[]::text[]) AS index_methods
        FROM column_base cb
        LEFT JOIN constraints_by_column cbc
          ON cbc.relation_oid = cb.relation_oid AND cbc.column_number = cb.column_number
        LEFT JOIN indexes_by_column ibc
          ON ibc.relation_oid = cb.relation_oid AND ibc.column_number = cb.column_number
        ORDER BY cb.schema_name, cb.table_name, cb.column_number;
    """
    async with client_postgres.acquire() as conn:
        records = await conn.fetch(sql)
    schema = {}
    for r in records:
        table_key = f"{r['schema_name']}.{r['table_name']}"
        table = schema.setdefault(table_key, {"schema_name": r["schema_name"], "table_name": r["table_name"], "relation_type": r["relation_type"], "columns": {}})
        index_methods = list(r["index_methods"] or [])
        table["columns"][r["column_name"]] = {
            "data_type": r["data_type"],
            "is_indexed": bool(index_methods),
            "index_methods": index_methods,
            "is_primary": r["is_primary"],
            "is_unique": bool(r["is_unique"] or r["is_unique_index"]),
        }
    return schema

def func_postgres_db_select(*, app_state: any, db: str = None) -> tuple:
    """Select target PostgreSQL client, schema, and AI schema caches by database pool name."""
    if db is None:
        return app_state.client_postgres, app_state.cache_postgres_schema, app_state.cache_postgres_schema_ai
    if not app_state.client_postgres_dict or db not in app_state.client_postgres_dict:
        raise Exception(f"database pool '{db}' not found")
    return (
        app_state.client_postgres_dict[db],
        app_state.cache_postgres_schema_dict.get(db, {}),
        app_state.cache_postgres_schema_ai_dict.get(db, {}),
    )

async def func_postgres_map_column(*, client_postgres: any, config_sql: str, is_json_value: bool = False) -> dict:
    """Execute a mapping SQL query and return a dictionary from the first two columns."""
    if not config_sql: return {}
    async with client_postgres.acquire() as conn:
        rows = await conn.fetch(config_sql)
    if not is_json_value: return {r[0]: r[1] for r in rows}
    import orjson
    output = {}
    for r in rows:
        value = r[1]
        if isinstance(value, (str, bytes, bytearray)): value = orjson.loads(value)
        output[r[0]] = value
    return output
