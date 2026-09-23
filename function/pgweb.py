"""Atom pgweb functions."""

def func_pgweb_ident(*parts) -> str:
    """Validate and quote PostgreSQL identifiers."""
    out = []
    for item in parts:
        if item in (None, ""): continue
        item = str(item)
        if not item.replace("_", "").isalnum(): raise Exception(f"invalid identifier: {item}")
        out.append(f'"{item}"')
    return ".".join(out)

def func_pgweb_jsonable(value):
    """Convert PostgreSQL values unsupported by the JSON encoder."""
    if value is None or isinstance(value, (bool, float, str)): return value
    if isinstance(value, int): return value if abs(value) <= 9007199254740991 else str(value)
    if isinstance(value, (bytes, bytearray, memoryview)): return "\\x" + bytes(value).hex()
    if isinstance(value, dict): return {str(key): func_pgweb_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)): return [func_pgweb_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        try: return value.isoformat()
        except (TypeError, ValueError): pass
    return str(value)

def func_pgweb_orjson_default(obj):
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return "\\x" + bytes(obj).hex()
    if hasattr(obj, "isoformat"):
        try: return obj.isoformat()
        except Exception: pass
    return str(obj)

def func_pgweb_orjson_dumps(payload: dict) -> bytes:
    """Fast C/Rust JSON serialization with automatic fallback for PostgreSQL data types."""
    import orjson
    return orjson.dumps(payload, default=func_pgweb_orjson_default)

def func_pgweb_pack(records) -> dict:
    """Pack asyncpg records for the browser grid with zero-copy row packing."""
    if not records: return {"cols": [], "rows": []}
    cols = [str(k) for k in records[0].keys()]
    return {"cols": cols, "rows": [list(r.values()) for r in records]}

def func_pgweb_dsn_safe(dsn: str) -> str:
    """Return connection context without exposing the password."""
    from urllib.parse import urlsplit, urlunsplit
    try:
        parsed = urlsplit(dsn)
        if not parsed.scheme: return dsn
        auth = parsed.username or ""
        if parsed.password is not None: auth += ":***"
        if auth: auth += "@"
        host = parsed.hostname or ""
        if ":" in host and not host.startswith("["): host = f"[{host}]"
        port = f":{parsed.port}" if parsed.port else ""
        return urlunsplit((parsed.scheme, f"{auth}{host}{port}", parsed.path, parsed.query, parsed.fragment))
    except Exception: return "connection URL unavailable"

async def func_pgweb_tree(*, pool: any, timeout_sec: int = 30) -> dict:
    """Read non-extension top-level tables, views, and materialized views in the public schema."""
    records = await pool.fetch("""
        SELECT n.nspname AS schema_name, c.relname AS name,
               CASE
                 WHEN c.relkind IN ('r','p') THEN 'table'
                 WHEN c.relkind = 'v' THEN 'view'
                 WHEN c.relkind = 'm' THEN 'materialized_view'
               END AS kind
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('r','p','v','m') AND n.nspname = 'public' AND NOT c.relispartition
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = c.oid AND d.classid = 'pg_class'::regclass AND d.deptype = 'e')
        ORDER BY n.nspname, c.relname""", timeout=timeout_sec)
    tree = {}
    for row in records: tree.setdefault(row["schema_name"], {}).setdefault(row["kind"], []).append({"name": row["name"]})
    return tree

async def func_pgweb_connect(*, client_postgres_pgweb: dict, func_client_postgres: callable, dsn: str = None, timeout_sec: int = 30) -> dict:
    """Create and register the pgweb connection pool."""
    from contextlib import suppress
    if not dsn: raise Exception("dsn is required")
    pool = await func_client_postgres(dsn=dsn, min_size=1, max_size=4)
    if not pool: raise Exception("could not connect")
    try:
        info = await pool.fetchrow("SELECT current_database() AS db, version() AS version", timeout=timeout_sec)
        tree = await func_pgweb_tree(pool=pool, timeout_sec=timeout_sec)
    except Exception:
        with suppress(Exception): await pool.close()
        raise
    previous = client_postgres_pgweb.pop("pool", None)
    if previous:
        with suppress(Exception): await previous.close()
    client_postgres_pgweb["pool"] = pool
    client_postgres_pgweb["connection_url"] = func_pgweb_dsn_safe(dsn)
    return {"tree": tree, "database": info["db"], "version": info["version"].split(" on ")[0]}

async def func_pgweb_disconnect(*, client_postgres_pgweb: dict) -> dict:
    """Close and remove the pgweb connection pool."""
    from contextlib import suppress
    pool = client_postgres_pgweb.pop("pool", None)
    client_postgres_pgweb.pop("connection_url", None)
    client_postgres_pgweb.pop("active_queries", None)
    if pool:
        with suppress(Exception): await pool.close()
    return {}

async def func_pgweb_schema(*, pool: any, timeout_sec: int = 30) -> dict:
    """Return the current database name and public table tree."""
    return {"tree": await func_pgweb_tree(pool=pool, timeout_sec=timeout_sec), "database": await pool.fetchval("SELECT current_database()", timeout=timeout_sec)}

async def func_pgweb_info(*, pool: any, connection_url: str, timeout_sec: int = 30) -> dict:
    """Return database properties plus user-owned and managed public object counts."""
    row = await pool.fetchrow("""
        SELECT current_database() AS database, current_user AS user_name, current_setting('server_version') AS version,
               pg_size_pretty(pg_database_size(current_database())) AS database_size,
               pg_encoding_to_char(d.encoding) AS encoding, d.datcollate AS collation, current_setting('TimeZone') AS time_zone
        FROM pg_database d WHERE d.datname = current_database()""", timeout=timeout_sec)
    relations = await pool.fetchrow("""
        SELECT count(*) FILTER (WHERE c.relkind IN ('r','p') AND NOT c.relispartition) AS tables,
               count(*) FILTER (WHERE c.relkind = 'v') AS views, count(*) FILTER (WHERE c.relkind = 'm') AS materialized_views,
               count(*) FILTER (WHERE c.relkind IN ('i','I')) AS indexes, count(*) FILTER (WHERE c.relkind = 'S') AS sequences
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = c.oid AND d.classid = 'pg_class'::regclass AND d.deptype = 'e')""", timeout=timeout_sec)
    routines = await pool.fetchrow("""
        SELECT count(*) FILTER (WHERE p.prokind IN ('f','w')) AS functions, count(*) FILTER (WHERE p.prokind = 'p') AS procedures
        FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public'
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = p.oid AND d.classid = 'pg_proc'::regclass AND d.deptype = 'e')""", timeout=timeout_sec)
    table_metadata = await pool.fetchrow("""
        WITH user_tables AS (
          SELECT c.oid FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          WHERE n.nspname='public' AND c.relkind IN ('r','p') AND NOT c.relispartition
            AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid=c.oid
              AND d.classid='pg_class'::regclass AND d.deptype='e')
        )
        SELECT
          (SELECT count(*) FROM pg_attribute a JOIN user_tables t ON t.oid=a.attrelid
             WHERE a.attnum>0 AND NOT a.attisdropped) AS columns,
          (SELECT count(*) FROM pg_constraint c JOIN user_tables t ON t.oid=c.conrelid) AS constraints,
          (SELECT count(*) FROM pg_constraint c JOIN user_tables t ON t.oid=c.conrelid WHERE c.contype='p') AS primary_keys,
          (SELECT count(*) FROM pg_constraint c JOIN user_tables t ON t.oid=c.conrelid WHERE c.contype='f') AS foreign_keys,
          (SELECT count(*) FROM pg_constraint c JOIN user_tables t ON t.oid=c.conrelid WHERE c.contype='u') AS unique_constraints,
          (SELECT count(*) FROM pg_policy p JOIN user_tables t ON t.oid=p.polrelid) AS policies
    """, timeout=timeout_sec)
    triggers = await pool.fetchval("""
        SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND NOT t.tgisinternal
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = t.oid AND d.classid = 'pg_trigger'::regclass AND d.deptype = 'e')
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = c.oid AND d.classid = 'pg_class'::regclass AND d.deptype = 'e')""", timeout=timeout_sec)
    managed = await pool.fetchrow("""
        SELECT
          (SELECT count(*) FROM pg_extension) AS extension_count,
          (SELECT string_agg(extname || ' ' || extversion, ', ' ORDER BY extname) FROM pg_extension) AS extension_names,
          (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'public' AND EXISTS (
               SELECT 1 FROM pg_depend d WHERE d.objid = c.oid
                 AND d.classid = 'pg_class'::regclass AND d.deptype = 'e')) AS extension_relations,
          (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'public' AND EXISTS (
               SELECT 1 FROM pg_depend d WHERE d.objid = p.oid
                 AND d.classid = 'pg_proc'::regclass AND d.deptype = 'e')) AS extension_routines,
          (SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
             JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'public' AND t.tgisinternal) AS internal_triggers
    """, timeout=timeout_sec)
    return {**{k: func_pgweb_jsonable(v) for k, v in row.items()}, "connection_url": connection_url,
            "schema_scope": "public", **{k: int(v) for k, v in relations.items()},
            **{k: int(v) for k, v in table_metadata.items()}, **{k: int(v) for k, v in routines.items()},
            "triggers": int(triggers),
            **{k: (int(v) if k != "extension_names" else (v or "None")) for k, v in managed.items()}}

async def func_pgweb_catalog(*, pool: any, kind: str, timeout_sec: int = 30) -> dict:
    """Return one lazily requested database-wide public-schema catalog."""
    columns_by_kind = {
        "tables": ["schema", "name", "type", "owner", "columns", "indexes", "constraints", "triggers", "policies", "size", "estimated_rows"],
        "columns": ["schema", "table_name", "position", "name", "type", "nullable", "default_value", "generated"],
        "views": ["schema", "name", "type", "owner", "size", "estimated_rows"],
        "materialized_views": ["schema", "name", "type", "owner", "size", "estimated_rows"],
        "indexes": ["schema", "name", "table_name", "method", "unique", "primary", "size", "definition"],
        "constraints": ["schema", "table_name", "name", "type", "columns", "references", "validated", "definition"],
        "primary_keys": ["schema", "table_name", "name", "type", "columns", "references", "validated", "definition"],
        "foreign_keys": ["schema", "table_name", "name", "type", "columns", "references", "validated", "definition"],
        "unique_constraints": ["schema", "table_name", "name", "type", "columns", "references", "validated", "definition"],
        "policies": ["schema", "table_name", "name", "mode", "command", "roles", "using_expression", "check_expression"],
        "sequences": ["schema", "name", "owner", "data_type", "start_value", "min_value", "max_value", "increment_by", "cycle"],
        "functions": ["schema", "name", "owner", "type", "arguments", "result", "language", "definition"],
        "procedures": ["schema", "name", "owner", "type", "arguments", "result", "language", "definition"],
        "triggers": ["schema", "table_name", "name", "enabled", "function", "definition"],
        "internal_triggers": ["schema", "table_name", "name", "enabled", "function", "definition"],
        "extensions": ["name", "version", "schema", "owner", "description"],
        "extension_relations": ["extension", "schema", "name", "type"],
        "extension_routines": ["extension", "schema", "name", "type", "arguments", "language"],
    }
    relation_kinds = {"tables": ("'r','p'", "Table"), "views": ("'v'", "View"),
                      "materialized_views": ("'m'", "Materialized view")}
    if kind in relation_kinds:
        relkinds, label = relation_kinds[kind]
        query = f"""
            SELECT n.nspname AS schema, c.relname AS name, $1::text AS type,
                   pg_get_userbyid(c.relowner) AS owner,
                   CASE WHEN c.relkind IN ('r','p') THEN
                     (SELECT count(*) FROM pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)
                   END AS columns,
                   CASE WHEN c.relkind IN ('r','p') THEN
                     (SELECT count(*) FROM pg_index i WHERE i.indrelid=c.oid)
                   END AS indexes,
                   CASE WHEN c.relkind IN ('r','p') THEN
                     (SELECT count(*) FROM pg_constraint con WHERE con.conrelid=c.oid)
                   END AS constraints,
                   CASE WHEN c.relkind IN ('r','p') THEN
                     (SELECT count(*) FROM pg_trigger t WHERE t.tgrelid=c.oid AND NOT t.tgisinternal)
                   END AS triggers,
                   CASE WHEN c.relkind IN ('r','p') THEN
                     (SELECT count(*) FROM pg_policy p WHERE p.polrelid=c.oid)
                   END AS policies,
                   CASE WHEN c.relkind IN ('r','p','m') THEN pg_size_pretty(pg_total_relation_size(c.oid)) ELSE '—' END AS size,
                   c.reltuples::bigint AS estimated_rows
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relkind IN ({relkinds}) AND NOT c.relispartition
              AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid=c.oid
                AND d.classid='pg_class'::regclass AND d.deptype='e')
            ORDER BY c.relname"""
        args = (label,)
    elif kind == "columns":
        query, args = """
            SELECT n.nspname AS schema, c.relname AS table_name, a.attnum AS position, a.attname AS name,
                   format_type(a.atttypid,a.atttypmod) AS type, NOT a.attnotnull AS nullable,
                   pg_get_expr(ad.adbin,ad.adrelid) AS default_value,
                   CASE a.attidentity WHEN 'a' THEN 'Identity always' WHEN 'd' THEN 'Identity by default'
                     ELSE CASE WHEN a.attgenerated<>'' THEN pg_get_expr(ad.adbin,ad.adrelid) END END AS generated
            FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
            LEFT JOIN pg_attrdef ad ON ad.adrelid=a.attrelid AND ad.adnum=a.attnum
            WHERE n.nspname='public' AND c.relkind IN ('r','p') AND NOT c.relispartition
              AND a.attnum>0 AND NOT a.attisdropped
              AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid=c.oid
                AND d.classid='pg_class'::regclass AND d.deptype='e')
            ORDER BY c.relname,a.attnum""", ()
    elif kind == "indexes":
        query, args = """
            SELECT n.nspname AS schema, i.relname AS name, t.relname AS table_name,
                   am.amname AS method, x.indisunique AS unique, x.indisprimary AS primary,
                   pg_size_pretty(pg_relation_size(i.oid)) AS size, pg_get_indexdef(i.oid) AS definition
            FROM pg_index x JOIN pg_class i ON i.oid=x.indexrelid JOIN pg_class t ON t.oid=x.indrelid
            JOIN pg_namespace n ON n.oid=i.relnamespace JOIN pg_am am ON am.oid=i.relam
            WHERE n.nspname='public' AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid=i.oid
              AND d.classid='pg_class'::regclass AND d.deptype='e') ORDER BY i.relname""", ()
    elif kind in ("constraints", "primary_keys", "foreign_keys", "unique_constraints"):
        constraint_type = {"constraints": None, "primary_keys": "p", "foreign_keys": "f", "unique_constraints": "u"}[kind]
        query, args = """
            SELECT n.nspname AS schema, c.relname AS table_name, con.conname AS name,
                   CASE con.contype WHEN 'p' THEN 'Primary key' WHEN 'f' THEN 'Foreign key'
                     WHEN 'u' THEN 'Unique' WHEN 'c' THEN 'Check' WHEN 'x' THEN 'Exclusion'
                     ELSE con.contype::text END AS type,
                   COALESCE((SELECT string_agg(a.attname, ', ' ORDER BY k.ord)
                     FROM unnest(con.conkey) WITH ORDINALITY k(attnum,ord)
                     JOIN pg_attribute a ON a.attrelid=con.conrelid AND a.attnum=k.attnum),'') AS columns,
                   CASE WHEN con.confrelid<>0 THEN con.confrelid::regclass::text END AS "references",
                   con.convalidated AS validated, pg_get_constraintdef(con.oid,true) AS definition
            FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND ($1::text IS NULL OR con.contype::text=$1)
              AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid=c.oid
                AND d.classid='pg_class'::regclass AND d.deptype='e')
            ORDER BY c.relname,con.conname""", (constraint_type,)
    elif kind == "policies":
        query, args = """
            SELECT schemaname AS schema, tablename AS table_name, policyname AS name,
                   CASE WHEN permissive='PERMISSIVE' THEN 'Permissive' ELSE 'Restrictive' END AS mode,
                   cmd AS command, COALESCE(array_to_string(roles,', '),'') AS roles,
                   qual AS using_expression, with_check AS check_expression
            FROM pg_policies p WHERE p.schemaname='public'
              AND NOT EXISTS (SELECT 1 FROM pg_depend d
                WHERE d.objid=(format('%I.%I',p.schemaname,p.tablename)::regclass)::oid
                  AND d.classid='pg_class'::regclass AND d.deptype='e')
            ORDER BY tablename,policyname""", ()
    elif kind == "sequences":
        query, args = """
            SELECT schemaname AS schema, sequencename AS name, sequenceowner AS owner, data_type,
                   start_value, min_value, max_value, increment_by, cycle
            FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename""", ()
    elif kind in ("functions", "procedures"):
        prokind = "p" if kind == "procedures" else "fw"
        query, args = """
            SELECT n.nspname AS schema, p.proname AS name, pg_get_userbyid(p.proowner) AS owner,
                   CASE p.prokind WHEN 'p' THEN 'Procedure' WHEN 'w' THEN 'Window function' ELSE 'Function' END AS type,
                   pg_get_function_identity_arguments(p.oid) AS arguments,
                   pg_get_function_result(p.oid) AS result, l.lanname AS language,
                   pg_get_functiondef(p.oid) AS definition
            FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang
            WHERE n.nspname='public' AND p.prokind::text = ANY($1::text[])
              AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid=p.oid
                AND d.classid='pg_proc'::regclass AND d.deptype='e')
            ORDER BY p.proname, pg_get_function_identity_arguments(p.oid)""", (list(prokind),)
    elif kind in ("triggers", "internal_triggers"):
        internal = kind == "internal_triggers"
        query, args = """
            SELECT n.nspname AS schema, c.relname AS table_name, t.tgname AS name,
                   CASE t.tgenabled WHEN 'D' THEN 'Disabled' WHEN 'R' THEN 'Replica' WHEN 'A' THEN 'Always' ELSE 'Enabled' END AS enabled,
                   p.proname AS function, pg_get_triggerdef(t.oid) AS definition
            FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
            JOIN pg_proc p ON p.oid=t.tgfoid WHERE n.nspname='public' AND t.tgisinternal=$1
              AND ($1 OR NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid=t.oid
                AND d.classid='pg_trigger'::regclass AND d.deptype='e'))
            ORDER BY c.relname,t.tgname""", (internal,)
    elif kind == "extensions":
        query, args = """
            SELECT e.extname AS name, e.extversion AS version, n.nspname AS schema,
                   pg_get_userbyid(e.extowner) AS owner, obj_description(e.oid,'pg_extension') AS description
            FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace ORDER BY e.extname""", ()
    elif kind == "extension_relations":
        query, args = """
            SELECT e.extname AS extension, n.nspname AS schema, c.relname AS name,
                   CASE c.relkind WHEN 'r' THEN 'Table' WHEN 'p' THEN 'Partitioned table' WHEN 'v' THEN 'View'
                     WHEN 'm' THEN 'Materialized view' WHEN 'i' THEN 'Index' WHEN 'S' THEN 'Sequence' ELSE c.relkind::text END AS type
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            JOIN pg_depend d ON d.objid=c.oid AND d.classid='pg_class'::regclass AND d.deptype='e'
            JOIN pg_extension e ON e.oid=d.refobjid WHERE n.nspname='public' ORDER BY e.extname,c.relname""", ()
    elif kind == "extension_routines":
        query, args = """
            SELECT e.extname AS extension, n.nspname AS schema, p.proname AS name,
                   CASE p.prokind WHEN 'p' THEN 'Procedure' WHEN 'w' THEN 'Window function' ELSE 'Function' END AS type,
                   pg_get_function_identity_arguments(p.oid) AS arguments, l.lanname AS language
            FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang
            JOIN pg_depend d ON d.objid=p.oid AND d.classid='pg_proc'::regclass AND d.deptype='e'
            JOIN pg_extension e ON e.oid=d.refobjid WHERE n.nspname='public' ORDER BY e.extname,p.proname""", ()
    else:
        raise Exception(f"invalid catalog: {kind}")
    records = await pool.fetch(query, *args, timeout=timeout_sec)
    rows = [{key: func_pgweb_jsonable(value) for key, value in dict(record).items()} for record in records]
    return {"columns": columns_by_kind[kind], "rows": rows}

async def func_pgweb_rows(*, pool: any, table: str, limit: int = 1000, offset: int = None, after: any = None,
                          filter_col: str = None, filter_op: str = None, filter_value: any = None, where: str = None,
                          order: str = None, is_desc: bool = False, pk: str = None, is_meta: bool = False, timeout_sec: int = 30) -> dict:
    """Read one public table page and optional grid metadata."""
    if not table: raise Exception("table is required")
    schema, limit, meta = "public", max(1, min(int(limit or 1000), 5000)), None
    if is_meta:
        reg = f"{schema}.{table}"
        catalog = await pool.fetch("""
            SELECT a.attnum AS position, a.attname AS name, format_type(a.atttypid, a.atttypmod) AS type,
                   NOT a.attnotnull AS nullable,
                   pg_get_expr(d.adbin, d.adrelid) AS default_value,
                   (SELECT string_agg(k.label, ', ' ORDER BY k.rank)
                    FROM (SELECT DISTINCT
                                 CASE con.contype WHEN 'p' THEN 'Primary' WHEN 'f' THEN 'Foreign' WHEN 'u' THEN 'Unique' END AS label,
                                 CASE con.contype WHEN 'p' THEN 1 WHEN 'f' THEN 2 WHEN 'u' THEN 3 END AS rank
                          FROM pg_constraint con
                          WHERE con.conrelid = c.oid AND a.attnum = ANY(con.conkey) AND con.contype IN ('p','f','u')) k) AS key_type,
                   CASE a.attidentity WHEN 'a' THEN 'Identity always' WHEN 'd' THEN 'Identity by default'
                     ELSE CASE WHEN a.attgenerated <> '' THEN pg_get_expr(d.adbin, d.adrelid) END END AS generated,
                   (SELECT pa.attname FROM pg_index i JOIN pg_attribute pa ON pa.attrelid = i.indrelid AND pa.attnum = ANY(i.indkey)
                    WHERE i.indrelid = a.attrelid AND i.indisprimary AND i.indnkeyatts = 1
                    ORDER BY array_position(i.indkey::smallint[], pa.attnum) LIMIT 1) AS pk,
                   pg_size_pretty(c.relpages::bigint * 8192) AS total_size
            FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
            LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
            WHERE a.attrelid = $1::regclass AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum""", reg, timeout=timeout_sec)
        first_meta = catalog[0] if catalog else None
        detected_pk = first_meta["pk"] if first_meta else None
        pk_type = next((str(row["type"]).lower() for row in catalog if row["name"] == detected_pk), "")
        latest_first = bool(detected_pk == "id" and any(kind in pk_type for kind in ("smallint", "integer", "bigint", "smallserial", "serial", "bigserial")))
        meta = {"columns": [{k: row[k] for k in ("position", "name", "type", "key_type", "nullable", "default_value", "generated")} for row in catalog],
                "pk": detected_pk, "latest_first": latest_first,
                "stats": {"total_size": first_meta["total_size"] if first_meta else "0 bytes"}}
        pk = pk or meta["pk"]
        if latest_first and not order: is_desc = True
    args, clauses = [], []
    if after not in (None, ""):
        if not pk: raise Exception("keyset paging requires a primary key")
        pk_type = await pool.fetchval("""
            SELECT format_type(a.atttypid, a.atttypmod)
            FROM pg_attribute a
            WHERE a.attrelid = $1::regclass AND a.attname = $2 AND a.attnum > 0 AND NOT a.attisdropped
        """, f"{schema}.{table}", pk, timeout=timeout_sec)
        if not pk_type: raise Exception(f"unknown primary key column: {pk}")
        args.append(str(after))
        clauses.append(f'{func_pgweb_ident(pk)} {"<" if is_desc else ">"} ($1::text)::{pk_type}')
    if where: raise Exception("raw where filters are not supported")
    if filter_col:
        operator = str(filter_op or "=").upper()
        allowed_operators = {"=", "<>", ">", "<", ">=", "<=", "LIKE", "ILIKE", "IS NULL", "IS NOT NULL"}
        if operator not in allowed_operators: raise Exception("invalid filter operator")
        column_type = await pool.fetchval("""
            SELECT format_type(a.atttypid, a.atttypmod)
            FROM pg_attribute a
            WHERE a.attrelid = $1::regclass AND a.attname = $2 AND a.attnum > 0 AND NOT a.attisdropped
        """, f"{schema}.{table}", filter_col, timeout=timeout_sec)
        if not column_type: raise Exception(f"unknown filter column: {filter_col}")
        column_sql = func_pgweb_ident(filter_col)
        if operator.startswith("IS "):
            clauses.append(f"{column_sql} {operator}")
        else:
            args.append("" if filter_value is None else str(filter_value))
            clauses.append(f"{column_sql} {operator} (${len(args)}::text)::{column_type}")
    where_sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    order_col = order or pk
    order_sql = f' ORDER BY {func_pgweb_ident(order_col)}{" DESC" if is_desc else ""}' if order_col else ""
    offset_sql = f" OFFSET {int(offset)}" if offset else ""
    records = await pool.fetch(f"SELECT * FROM {func_pgweb_ident(schema, table)}{where_sql}{order_sql} LIMIT {limit + 1}{offset_sql}", *args, timeout=timeout_sec)
    out = func_pgweb_pack(records[:limit])
    out["has_more"] = len(records) > limit
    if meta is not None: out["meta"] = meta
    return out

async def func_pgweb_query(*, pool: any, sql: str, is_confirmed: bool = False, is_read_only: bool = False,
                           query_id: str = None, active_queries: dict = None, timeout_sec: int = 30) -> dict:
    """Execute query-runner SQL with write guards and optional read-only mode."""
    if not sql or not sql.strip(): raise Exception("sql is required")
    normalized = " ".join(sql.lower().split())
    if not is_read_only and not is_confirmed and (normalized.startswith(("truncate", "drop ")) or (normalized.startswith(("update ", "delete ")) and " where " not in normalized)): raise Exception("unbounded_write")
    result_limit = 10000
    async with pool.acquire() as conn:
        backend_pid = await conn.fetchval("SELECT pg_backend_pid()", timeout=timeout_sec)
        if query_id and active_queries is not None: active_queries[query_id] = backend_pid
        try:
            async with conn.transaction(readonly=bool(is_read_only)):
                try:
                    async with conn.transaction():
                        statement = await conn.prepare(sql, timeout=timeout_sec)
                except Exception as exc:
                    if "multiple commands" not in str(exc).lower(): raise
                    status = await conn.execute(sql, timeout=timeout_sec)
                    return {"cols": ["status"], "rows": [[status]], "truncated": False}
                if not statement.get_attributes():
                    return func_pgweb_pack(await statement.fetch(timeout=timeout_sec))
                cursor = await statement.cursor(timeout=timeout_sec)
                records = await cursor.fetch(result_limit + 1)
                out = func_pgweb_pack(records[:result_limit])
                out["truncated"] = len(records) > result_limit
                return out
        finally:
            if query_id and active_queries is not None and active_queries.get(query_id) == backend_pid:
                active_queries.pop(query_id, None)

async def func_pgweb_stream(*, pool: any, sql: str, is_confirmed: bool = False, is_read_only: bool = False, timeout_sec: int = 300) -> any:
    """Stream every row returned by one query as CSV without buffering the result set."""
    import csv
    import io
    if not sql or not sql.strip(): raise Exception("sql is required")
    normalized = " ".join(sql.lower().split())
    if not is_read_only and not is_confirmed and (normalized.startswith(("truncate", "drop ")) or (normalized.startswith(("update ", "delete ")) and " where " not in normalized)): raise Exception("unbounded_write")
    async with pool.acquire() as conn:
        try: statement = await conn.prepare(sql, timeout=timeout_sec)
        except Exception as exc:
            if "multiple commands" in str(exc).lower(): raise Exception("stream supports one row-returning statement") from exc
            raise
        columns = [attr.name for attr in statement.get_attributes()]
    if not columns: raise Exception("query returned no downloadable rows")

    async def _iter():
        async with pool.acquire() as conn:
            async with conn.transaction(readonly=bool(is_read_only)):
                await conn.execute(f"SET LOCAL statement_timeout = '{int(timeout_sec) * 1000}ms'")
                statement = await conn.prepare(sql, timeout=timeout_sec)
                buffer = io.StringIO()
                writer = csv.writer(buffer)
                writer.writerow(columns)
                yield buffer.getvalue().encode("utf-8")
                buffer.seek(0); buffer.truncate(0)
                pending = 0
                async for record in statement.cursor(prefetch=500, timeout=timeout_sec):
                    writer.writerow([func_pgweb_jsonable(record[column]) for column in columns])
                    pending += 1
                    if pending >= 250:
                        yield buffer.getvalue().encode("utf-8")
                        buffer.seek(0); buffer.truncate(0); pending = 0
                if pending: yield buffer.getvalue().encode("utf-8")
    return _iter()

async def func_pgweb_detail(*, pool: any, table: str, part: str, timeout_sec: int = 30) -> dict:
    """Read one lazily loaded public-table detail."""
    if not table: raise Exception("table is required")
    schema, reg = "public", f"public.{table}"
    if part == "overview": query, args = """
        SELECT n.nspname AS schema, pg_get_userbyid(c.relowner) AS owner,
               CASE c.relkind WHEN 'r' THEN 'Table' WHEN 'p' THEN 'Partitioned table'
                 WHEN 'v' THEN 'View' WHEN 'm' THEN 'Materialized view' WHEN 'f' THEN 'Foreign table'
                 ELSE c.relkind::text END AS kind,
               c.reltuples::bigint AS estimated_rows,
               pg_size_pretty(pg_table_size(c.oid)) AS table_size,
               pg_size_pretty(pg_indexes_size(c.oid)) AS index_size,
               pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
               COALESCE(ts.spcname, 'pg_default') AS tablespace,
               CASE c.relpersistence WHEN 'p' THEN 'Permanent' WHEN 'u' THEN 'Unlogged' WHEN 't' THEN 'Temporary' END AS persistence,
               CASE WHEN c.relrowsecurity THEN CASE WHEN c.relforcerowsecurity THEN 'Forced' ELSE 'Enabled' END ELSE 'Disabled' END AS rls,
               obj_description(c.oid, 'pg_class') AS comment
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        LEFT JOIN pg_tablespace ts ON ts.oid = c.reltablespace
        WHERE c.oid = $1::regclass""", (reg,)
    elif part == "indexes": query, args = """
        SELECT idx.relname AS name, am.amname AS method,
               (SELECT string_agg(pg_get_indexdef(i.indexrelid, n, true), ', ' ORDER BY n)
                FROM generate_series(1, i.indnkeyatts) n) AS columns,
               i.indisunique AS is_unique, i.indisprimary AS is_primary,
               pg_size_pretty(pg_relation_size(idx.oid)) AS size,
               pg_get_expr(i.indpred, i.indrelid) AS predicate,
               pg_get_indexdef(i.indexrelid, 0, true) AS def
        FROM pg_index i JOIN pg_class idx ON idx.oid = i.indexrelid
        JOIN pg_am am ON am.oid = idx.relam
        WHERE i.indrelid = $1::regclass ORDER BY idx.relname""", (reg,)
    elif part == "constraints": query, args = """
        SELECT con.conname AS name,
               CASE con.contype WHEN 'p' THEN 'Primary key' WHEN 'f' THEN 'Foreign key' WHEN 'u' THEN 'Unique'
                 WHEN 'c' THEN 'Check' WHEN 'x' THEN 'Exclude' ELSE con.contype::text END AS kind,
               (SELECT string_agg(a.attname, ', ' ORDER BY keys.ord)
                FROM unnest(con.conkey) WITH ORDINALITY keys(attnum, ord)
                JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = keys.attnum) AS columns,
               CASE WHEN con.contype = 'f' THEN con.confrelid::regclass::text || ' (' ||
                 (SELECT string_agg(a.attname, ', ' ORDER BY keys.ord)
                  FROM unnest(con.confkey) WITH ORDINALITY keys(attnum, ord)
                  JOIN pg_attribute a ON a.attrelid = con.confrelid AND a.attnum = keys.attnum) || ')' END AS reference,
               con.condeferrable AS deferrable, con.convalidated AS validated,
               pg_get_constraintdef(con.oid) AS def
        FROM pg_constraint con WHERE con.conrelid = $1::regclass AND con.contype <> 'n'
        ORDER BY con.contype, con.conname""", (reg,)
    elif part == "statistics": query, args = """
        SELECT COALESCE(s.seq_scan, 0) AS seq_scan, COALESCE(s.idx_scan, 0) AS idx_scan,
               COALESCE(s.n_live_tup, 0) AS live_rows, COALESCE(s.n_dead_tup, 0) AS dead_rows,
               COALESCE(s.n_tup_ins, 0) AS inserts, COALESCE(s.n_tup_upd, 0) AS updates,
               COALESCE(s.n_tup_del, 0) AS deletes, COALESCE(s.n_tup_hot_upd, 0) AS hot_updates,
               s.last_vacuum::text, s.last_autovacuum::text, s.last_analyze::text, s.last_autoanalyze::text,
               COALESCE(io.heap_blks_hit, 0) AS heap_hits, COALESCE(io.heap_blks_read, 0) AS heap_reads,
               COALESCE(io.idx_blks_hit, 0) AS index_hits, COALESCE(io.idx_blks_read, 0) AS index_reads
        FROM pg_stat_user_tables s
        LEFT JOIN pg_statio_user_tables io ON io.relid = s.relid
        WHERE s.relid = $1::regclass""", (reg,)
    elif part == "ddl": query, args = """
        WITH relation AS (
          SELECT c.oid, c.relkind, n.nspname AS schema_name, c.relname
          FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.oid = $1::regclass
        ), column_lines AS (
          SELECT string_agg(format('%I %s%s%s', a.attname, format_type(a.atttypid, a.atttypmod),
                   CASE WHEN a.attidentity = 'a' THEN ' GENERATED ALWAYS AS IDENTITY'
                        WHEN a.attidentity = 'd' THEN ' GENERATED BY DEFAULT AS IDENTITY'
                        WHEN a.attgenerated = 's' THEN format(' GENERATED ALWAYS AS (%s) STORED', pg_get_expr(ad.adbin, ad.adrelid))
                        WHEN ad.adbin IS NOT NULL THEN ' DEFAULT ' || pg_get_expr(ad.adbin, ad.adrelid) ELSE '' END,
                   CASE WHEN a.attnotnull THEN ' NOT NULL' ELSE '' END), E',\n  ' ORDER BY a.attnum) AS lines
          FROM relation r JOIN pg_attribute a ON a.attrelid = r.oid
          LEFT JOIN pg_attrdef ad ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
          WHERE a.attnum > 0 AND NOT a.attisdropped
        ), constraint_lines AS (
          SELECT string_agg(format('CONSTRAINT %I %s', con.conname, pg_get_constraintdef(con.oid, true)), E',\n  ' ORDER BY con.conname) AS lines
          FROM relation r JOIN pg_constraint con ON con.conrelid = r.oid WHERE con.contype <> 'n'
        ), statements AS (
          SELECT 1 AS ord, 'Relation'::text AS kind, r.relname AS name,
                 CASE WHEN r.relkind = 'v' THEN format('CREATE VIEW %I.%I AS\n%s;', r.schema_name, r.relname, pg_get_viewdef(r.oid, true))
                      WHEN r.relkind = 'm' THEN format('CREATE MATERIALIZED VIEW %I.%I AS\n%s;', r.schema_name, r.relname, pg_get_viewdef(r.oid, true))
                      ELSE format('CREATE TABLE %I.%I (\n  %s%s\n);', r.schema_name, r.relname, COALESCE(c.lines, ''),
                                  CASE WHEN k.lines IS NULL THEN '' ELSE E',\n  ' || k.lines END) END AS sql
          FROM relation r CROSS JOIN column_lines c CROSS JOIN constraint_lines k
          UNION ALL
          SELECT 2, 'Index', idx.relname, pg_get_indexdef(i.indexrelid, 0, true) || ';'
          FROM relation r JOIN pg_index i ON i.indrelid = r.oid JOIN pg_class idx ON idx.oid = i.indexrelid
          WHERE NOT EXISTS (SELECT 1 FROM pg_constraint con WHERE con.conindid = i.indexrelid)
          UNION ALL
          SELECT 3, 'Trigger', t.tgname, pg_get_triggerdef(t.oid, true) || ';'
          FROM relation r JOIN pg_trigger t ON t.tgrelid = r.oid WHERE NOT t.tgisinternal
        ) SELECT kind, name, sql FROM statements ORDER BY ord, name""", (reg,)
    elif part == "triggers": query, args = """
        SELECT t.tgname AS name,
               CASE WHEN (t.tgtype & 64) <> 0 THEN 'Instead of' WHEN (t.tgtype & 2) <> 0 THEN 'Before' ELSE 'After' END AS timing,
               concat_ws(', ', CASE WHEN (t.tgtype & 4) <> 0 THEN 'Insert' END,
                 CASE WHEN (t.tgtype & 16) <> 0 THEN 'Update' END,
                 CASE WHEN (t.tgtype & 8) <> 0 THEN 'Delete' END,
                 CASE WHEN (t.tgtype & 32) <> 0 THEN 'Truncate' END) AS events,
               CASE WHEN (t.tgtype & 1) <> 0 THEN 'Row' ELSE 'Statement' END AS level,
               p.proname AS function,
               CASE t.tgenabled WHEN 'O' THEN 'Enabled' WHEN 'D' THEN 'Disabled' WHEN 'R' THEN 'Replica' WHEN 'A' THEN 'Always' END AS enabled,
               pg_get_expr(t.tgqual, t.tgrelid) AS condition, pg_get_triggerdef(t.oid) AS def
        FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
        WHERE t.tgrelid = $1::regclass AND NOT t.tgisinternal ORDER BY t.tgname""", (reg,)
    elif part == "policies": query, args = "SELECT policyname AS name, permissive AS mode, cmd AS kind, COALESCE(array_to_string(roles, ', '), '') AS roles, COALESCE(qual, '') AS using_expr, COALESCE(with_check, '') AS check_expr FROM pg_policies WHERE schemaname = $1 AND tablename = $2 ORDER BY policyname", (schema, table)
    elif part == "privileges": query, args = """
        SELECT grantee, string_agg(privilege_type, ', ' ORDER BY privilege_type) AS privileges,
               grantor, CASE WHEN bool_or(is_grantable = 'YES') THEN 'Yes' ELSE 'No' END AS grantable
        FROM information_schema.role_table_grants
        WHERE table_schema = $1 AND table_name = $2
        GROUP BY grantee, grantor ORDER BY grantee, grantor""", (schema, table)
    elif part == "partitions": query, args = """
        SELECT n.nspname AS schema, c.relname AS name, pg_get_expr(c.relpartbound, c.oid, true) AS bound,
               c.reltuples::bigint AS estimated_rows, pg_size_pretty(pg_total_relation_size(c.oid)) AS size,
               COALESCE(ts.spcname, 'pg_default') AS tablespace
        FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace LEFT JOIN pg_tablespace ts ON ts.oid = c.reltablespace
        WHERE i.inhparent = $1::regclass ORDER BY n.nspname, c.relname""", (reg,)
    elif part == "dependencies": query, args = """
        SELECT DISTINCT kind, name, relationship FROM (
          SELECT 'View'::text AS kind, nv.nspname || '.' || v.relname AS name, 'References this table'::text AS relationship
          FROM pg_depend d JOIN pg_rewrite rw ON rw.oid = d.objid JOIN pg_class v ON v.oid = rw.ev_class
          JOIN pg_namespace nv ON nv.oid = v.relnamespace
          WHERE d.refobjid = $1::regclass AND v.oid <> d.refobjid AND v.relkind IN ('v','m')
          UNION ALL
          SELECT 'Foreign key', con.conrelid::regclass::text || '.' || con.conname, 'References this table'
          FROM pg_constraint con WHERE con.confrelid = $1::regclass
          UNION ALL
          SELECT 'Sequence', ns.nspname || '.' || seq.relname, 'Owned by this table'
          FROM pg_depend d JOIN pg_class seq ON seq.oid = d.objid AND seq.relkind = 'S'
          JOIN pg_namespace ns ON ns.oid = seq.relnamespace
          WHERE d.refobjid = $1::regclass AND d.deptype IN ('a','i')
        ) deps ORDER BY kind, name""", (reg,)
    else: raise Exception(f"invalid part: {part}")
    return {"rows": [dict(row) for row in await pool.fetch(query, *args, timeout=timeout_sec)]}

async def func_pgweb(*, app_state: any, action: str, **params) -> dict:
    """Dispatch pgweb actions through focused app-state handlers."""
    client_postgres_pgweb = app_state.client_postgres_pgweb
    if action == "connect": return await app_state.func_pgweb_connect(client_postgres_pgweb=client_postgres_pgweb, func_client_postgres=app_state.func_client_postgres, **params)
    if action == "disconnect": return await app_state.func_pgweb_disconnect(client_postgres_pgweb=client_postgres_pgweb)
    pool = client_postgres_pgweb.get("pool")
    if not pool: raise Exception("not_connected")
    active_queries = client_postgres_pgweb.setdefault("active_queries", {})
    if action == "cancel":
        query_id = str(params.get("query_id") or "")
        backend_pid = active_queries.get(query_id)
        canceled = bool(backend_pid and await pool.fetchval("SELECT pg_cancel_backend($1)", backend_pid))
        return {"canceled": canceled}
    handlers = {"schema": app_state.func_pgweb_schema, "info": app_state.func_pgweb_info,
                "catalog": app_state.func_pgweb_catalog, "rows": app_state.func_pgweb_rows,
                "query": app_state.func_pgweb_query, "detail": app_state.func_pgweb_detail}
    handler = handlers.get(action)
    if not handler: raise Exception(f"invalid action: {action}")
    if action == "info": params["connection_url"] = client_postgres_pgweb.get("connection_url", "—")
    if action == "query": params["active_queries"] = active_queries
    return await handler(pool=pool, **params)
