async def func_postgres_schema_read(*, client_postgres_pool: any) -> dict:
    """Read full database schema as a simplified dictionary."""
    async with client_postgres_pool.acquire() as conn:
        rows = await conn.fetch("SELECT table_name, column_name, CASE WHEN data_type = 'ARRAY' THEN ltrim(udt_name, '_') || '[]' WHEN data_type = 'USER-DEFINED' THEN udt_name ELSE data_type END AS data_type FROM information_schema.columns WHERE table_schema = 'public'")
        schema = {}
        for r in rows:
            table = r["table_name"]
            col = r["column_name"]
            if table not in schema:
                schema[table] = {}
            schema[table][col] = r["data_type"]
    return schema

async def func_postgres_serialize(*, client_postgres_pool: any, cache_postgres_schema: dict, table: str, obj_list: list, is_base: int) -> list:
    """Serialize Python objects (JSON, Arrays, Geog) to PostgreSQL compatible formats using schema-aware injection."""
    output_list = []
    import orjson, hashlib
    if table not in cache_postgres_schema:
        return obj_list
    schema = cache_postgres_schema[table]
    for item in obj_list:
        new_item = {}
        for col, val in item.items():
            if table == "users" and col == "password" and val:
                val = hashlib.sha256(str(val).encode()).hexdigest()
            if col not in schema:
                if col == "id":
                    new_item[col] = val
                continue
            if val is None:
                new_item[col] = val
                continue
            dtype = schema[col].lower()
            val_str = str(val).strip()
            base_dtype = schema[col].lower().replace("[]", "").replace("array", "").strip()
            def cast_val(v, t):
                vs = str(v).strip()
                if not vs or vs.lower() == "null":
                    return None
                if any(x in t for x in ("int", "serial", "bigint")):
                    return int(vs)
                if "bool" in t:
                    return 1 if vs.lower() in ("true", "1", "yes", "on", "ok") else 0
                if any(x in t for x in ("numeric", "float", "double")):
                    return float(vs)
                if "timestamp" in t:
                    from datetime import datetime
                    if isinstance(v, str):
                        return datetime.fromisoformat(vs.replace("Z", "+00:00"))
                    return v
                if "date" in t:
                    from datetime import date
                    if isinstance(v, str):
                        return date.fromisoformat(vs)
                    return v
                return v
            if is_base == 1:
                if "json" in dtype:
                    new_item[col] = orjson.dumps(val).decode('utf-8') if not isinstance(val, str) else val
                elif "[]" in dtype or "array" in dtype:
                    v_arr = val_str.strip("{}")
                    arr = val if isinstance(val, (list, tuple)) else ([x.strip() for x in v_arr.split(",")] if v_arr else [])
                    new_item[col] = [cast_val(x, base_dtype) for x in arr]
                else:
                    new_item[col] = cast_val(val, dtype)
            else:
                if "json" in dtype:
                    if isinstance(val, str):
                        new_item[col] = orjson.loads(val_str) if val_str.startswith(("{", "[")) else val_str
                    else:
                        new_item[col] = orjson.dumps(val).decode('utf-8')
                elif "[]" in dtype or "array" in dtype:
                    v_arr = val_str.strip("{}")
                    arr = val if isinstance(val, (list, tuple)) else ([x.strip() for x in v_arr.split(",")] if v_arr else [])
                    new_item[col] = [cast_val(x, base_dtype) for x in arr]
                elif "bytea" in dtype:
                    new_item[col] = val.encode() if isinstance(val, str) else val
                else:
                    new_item[col] = cast_val(val, dtype)
        output_list.append(new_item)
    return output_list

async def func_postgres_schema_init(*, client_postgres_pool: any, config_postgres: dict) -> str:
    """Initialize PostgreSQL database schema, tables, indexes, constraints, and triggers based on configuration."""
    if not config_postgres:
        raise Exception("config_postgres missing")
    if "table" not in config_postgres:
        raise Exception("config_postgres.table missing")
    control = config_postgres.get("control", {})
    is_ext = control.get("is_extension", 0)
    bulk_blocked = control.get("table_delete_disable_row_bulk", [])
    table_blocked = control.get("table_delete_disable_row", [])
    is_autovacuum = control.get("is_autovacuum_optimize", 0)
    is_drop_schema = control.get("is_drop_disable_schema", 0)
    is_drop_table = control.get("is_drop_disable_table", 0)
    is_truncate_table = control.get("is_truncate_disable", 0)
    catalog = {"idx": set(), "uni": set(), "chk": set(), "tg": set()}
    reserved = {"all", "analyze", "and", "any", "as", "asc", "asymmetric", "authorization", "binary", "both", "case", "cast", "check", "collate", "collation", "column", "concurrently", "constraint", "create", "cross", "current_catalog", "current_date", "current_role", "current_schema", "current_time", "current_timestamp", "current_user", "default", "deferrable", "desc", "distinct", "do", "else", "end", "except", "false", "fetch", "for", "foreign", "freeze", "from", "full", "grant", "group", "having", "ilike", "in", "initially", "inner", "intersect", "into", "is", "isnull", "join", "lateral", "leading", "left", "like", "limit", "localtime", "localtimestamp", "natural", "not", "notnull", "null", "offset", "on", "only", "or", "order", "outer", "overlaps", "placing", "primary", "references", "returning", "right", "select", "session_user", "similar", "some", "symmetric", "table", "tablesample", "then", "to", "trailing", "true", "union", "unique", "user", "using", "variadic", "verbose", "when", "where", "window", "with"}
    for table_name, column_configs in config_postgres["table"].items():
        column_names = set()
        for col in column_configs:
            name, dtype = col.get("name"), col.get("datatype")
            if not name or not dtype:
                raise Exception(f"Missing mandatory key 'name' or 'datatype' in {table_name} column: {col}")
            if name.lower() in reserved:
                raise Exception(f"Column name '{name}' in table '{table_name}' is a PostgreSQL reserved keyword. Please rename it.")
            if name in column_names:
                raise Exception(f"Duplicate column name '{name}' in table '{table_name}'")
            column_names.add(name)
            
            # Regex validation
            if "regex" in col and "[]" in dtype.lower():
                raise Exception(f"Regex constraint is not supported for array column {table_name}.{name}. Remove 'regex' key to resolve.")
            
            # Index Compatibility
            indices = [i.strip() for i in col.get("index", "").split(",") if i.strip()]
            for idx in indices:
                if idx.lower() == "gin":
                    if not any(x in dtype.lower() for x in ("[]", "jsonb", "text", "varchar")):
                        raise Exception(f"GIN index is not compatible with '{dtype}' on {table_name}.{name}. Supported: arrays, jsonb, text, varchar.")
                if idx.lower() == "gist":
                    if not any(x in dtype.lower() for x in ("geography", "geometry", "box", "circle", "point", "polygon")):
                        raise Exception(f"GIST index is not compatible with '{dtype}' on {table_name}.{name}. Supported: geography, geometry, spatial types.")
            
            # Spatial Enforcement
            if any(x in dtype.lower() for x in ("geography", "geometry")):
                if indices and not any(x.lower() == "gist" for x in indices):
                    raise Exception(f"Spatial column {table_name}.{name} must use 'gist' index if indexed.")

        # Unique Constraints Cross-Reference
        for col in column_configs:
            if col.get("unique"):
                for group in col["unique"].split("|"):
                    for u_col in (x.strip() for x in group.split(",") if x.strip()):
                        if u_col not in column_names:
                            raise Exception(f"Unique constraint in {table_name} references non-existent column '{u_col}'. Defined columns: {list(column_names)}")
    async with client_postgres_pool.acquire() as conn:
        if is_ext:
            for extension in ("postgis", "pg_trgm", "btree_gin"):
                await conn.execute(f"CREATE EXTENSION IF NOT EXISTS {extension};")
        for table_name, column_configs in config_postgres["table"].items():
            await conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (id BIGSERIAL PRIMARY KEY);")
            if is_autovacuum:
                await conn.execute(f"ALTER TABLE {table_name} SET (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);")
            rows = await conn.fetch("SELECT a.attname, format_type(a.atttypid, a.atttypmod) as type, a.attnotnull as notnull, pg_get_expr(ad.adbin, ad.adrelid) as default FROM pg_attribute a JOIN pg_class t ON a.attrelid = t.oid JOIN pg_namespace n ON t.relnamespace = n.oid LEFT JOIN pg_attrdef ad ON a.attrelid = ad.adrelid AND a.attnum = ad.adnum WHERE t.relname = $1 AND n.nspname = 'public' AND a.attnum > 0 AND NOT a.attisdropped", table_name)
            current_cols = {r[0]: r[1] for r in rows}
            current_notnulls = {r[0]: r[2] for r in rows}
            current_defaults = {r[0]: r[3] for r in rows}
            for col_cfg in column_configs:
                col_name = col_cfg["name"]
                col_type = col_cfg["datatype"]
                if col_name not in current_cols:
                    old_name = col_cfg.get("old")
                    if old_name and old_name in current_cols:
                        await conn.execute(f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {col_name}")
                        current_cols[col_name] = current_cols.pop(old_name)
                        current_notnulls[col_name] = current_notnulls.pop(old_name)
                    else:
                        default_val = f"""DEFAULT {col_cfg["default"]}""" if "default" in col_cfg else ""
                        mandatory_val = "NOT NULL" if col_cfg.get("is_mandatory") == 1 else ""
                        await conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {default_val} {mandatory_val}")
                        current_cols[col_name] = col_type.split("(")[0].lower()
                        current_notnulls[col_name] = (col_cfg.get("is_mandatory") == 1)
                else:
                    type_mapping = {"timestamp with time zone": "timestamptz", "character varying": "varchar", "integer": "int", "boolean": "bool"}
                    current_type = type_mapping.get(current_cols[col_name].lower().split("(")[0], current_cols[col_name].lower().split("(")[0])
                    target_type = type_mapping.get(col_type.lower().split("(")[0], col_type.lower().split("(")[0])
                    if type_mapping.get(current_cols[col_name].lower().split("(")[0], current_cols[col_name].lower().split("(")[0]) != type_mapping.get(col_type.lower().split("(")[0], col_type.lower().split("(")[0]):
                        await conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} TYPE {col_type} USING {col_name}::{col_type}")
                    target_notnull = (col_cfg.get("is_mandatory") == 1)
                    if current_notnulls[col_name] != target_notnull:
                        if target_notnull:
                            await conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} SET NOT NULL")
                        else:
                            await conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} DROP NOT NULL")
                    target_default = str(col_cfg.get("default")).strip() if "default" in col_cfg else None
                    current_default = current_defaults.get(col_name)
                    if target_default:
                        if current_default is None or target_default not in current_default:
                             await conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} SET DEFAULT {target_default}")
                    elif current_default is not None:
                        await conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} DROP DEFAULT")
            for col_cfg in column_configs:
                col_name = col_cfg["name"]
                col_type = col_cfg["datatype"]
                if col_cfg.get("index"):
                    for index_type in (x.strip() for x in col_cfg["index"].split(",")):
                        idx_name = f"idx_{table_name}_{col_name}_{index_type}"
                        catalog["idx"].add(idx_name)
                        if idx_name not in [r[0] for r in await conn.fetch("SELECT indexname FROM pg_indexes WHERE tablename=$1", table_name)]:
                            ops = "gin_trgm_ops" if index_type == "gin" and "text" in col_type.lower() and "[]" not in col_type.lower() else ""
                            await conn.execute(f"CREATE INDEX {idx_name} ON {table_name} USING {index_type}({col_name} {ops});")
                if "in" in col_cfg:
                    chk_name = f"check_{table_name}_{col_name}_in"
                    catalog["chk"].add(chk_name)
                    await conn.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {chk_name}")
                    await conn.execute(f"""ALTER TABLE {table_name} ADD CONSTRAINT {chk_name} CHECK ({col_name} IN {col_cfg["in"]});""")
                if "regex" in col_cfg:
                    regex_name = f"check_{table_name}_{col_name}_regex"
                    catalog["chk"].add(regex_name)
                    await conn.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {regex_name}")
                    await conn.execute(f"""ALTER TABLE {table_name} ADD CONSTRAINT {regex_name} CHECK ({col_name} ~ '{col_cfg["regex"]}');""")
                if "check" in col_cfg:
                    vld_name = f"check_{table_name}_{col_name}_vld"
                    catalog["chk"].add(vld_name)
                    await conn.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {vld_name}")
                    await conn.execute(f"""ALTER TABLE {table_name} ADD CONSTRAINT {vld_name} CHECK ({col_cfg["check"]});""")
                if col_cfg.get("unique"):
                    for group in col_cfg["unique"].split("|"):
                        unique_cols = [x.strip() for x in group.split(",")]
                        uni_name = f"""unique_{table_name}_{"_".join(unique_cols)}"""
                        catalog["uni"].add(uni_name)
                        await conn.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {uni_name}")
                        await conn.execute(f"""ALTER TABLE {table_name} ADD CONSTRAINT {uni_name} UNIQUE ({",".join(unique_cols)});""")
            configured_cols = {cfg["name"] for cfg in column_configs} | {"id"}
            db_cols = set(current_cols.keys())
            if db_cols - configured_cols:
                raise Exception(f"Database mismatch for table '{table_name}': columns {db_cols - configured_cols} exist in DB but are not in config. Manual cleanup required.")
        db_schema_rows = await conn.fetch("SELECT c.table_name, c.column_name FROM information_schema.columns c JOIN information_schema.tables t ON c.table_name = t.table_name AND c.table_schema = t.table_schema WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE'")
        db_tables = {}
        for row in db_schema_rows:
            db_tables.setdefault(row[0], []).append(row[1])
        users_cols = db_tables.get("users", [])
        if users_cols:
            catalog["tg"].add("trigger_no_delete_root_users")
            await conn.execute("CREATE OR REPLACE FUNCTION func_no_delete_root_users() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.id = 1 THEN RAISE EXCEPTION 'DELETE not allowed for root user (id=1)'; END IF; RETURN OLD; END; $$; DROP TRIGGER IF EXISTS trigger_no_delete_root_users ON users; CREATE TRIGGER trigger_no_delete_root_users BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_no_delete_root_users();")
            if all(c in users_cols for c in ("type", "username", "password", "role", "is_active")):
                root_user_password = control.get("root_user_password", "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3")
                await conn.execute("INSERT INTO users (id, type, username, password, role, is_active) VALUES (1, 1, 'atom', $1, 1, 1) ON CONFLICT (id) DO UPDATE SET password = EXCLUDED.password, role = 1, is_active = 1 WHERE users.password IS DISTINCT FROM EXCLUDED.password;", root_user_password)
            if "password" in users_cols and "log_users_password" in db_tables:
                catalog["tg"].add("trigger_password_log_users")
                await conn.execute("CREATE OR REPLACE FUNCTION func_password_log_users() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.password IS DISTINCT FROM NEW.password THEN INSERT INTO log_users_password (user_id, password) VALUES (NEW.id, NEW.password); END IF; RETURN NEW; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_password_log_users ON users; CREATE TRIGGER trigger_password_log_users AFTER UPDATE ON users FOR EACH ROW EXECUTE FUNCTION func_password_log_users();")
            if control.get("is_users_delete_child_soft", 0) and "is_deleted" in users_cols:
                catalog["tg"].add("trigger_soft_delete_users")
                await conn.execute("CREATE OR REPLACE FUNCTION func_soft_delete_users() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE r RECORD; v INTEGER; BEGIN v := (CASE WHEN NEW.is_deleted=1 THEN 1 ELSE NULL END); FOR r IN SELECT table_schema, table_name, column_name FROM information_schema.columns WHERE column_name IN ('created_by_id', 'user_id') AND table_name NOT IN ('users', 'spatial_ref_sys') AND table_schema NOT IN ('information_schema', 'pg_catalog') LOOP IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = r.table_schema AND table_name = r.table_name AND column_name = 'is_deleted') THEN EXECUTE format('UPDATE %I.%I SET is_deleted = $1 WHERE %I = $2', r.table_schema, r.table_name, r.column_name) USING v, NEW.id; END IF; END LOOP; RETURN NEW; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_soft_delete_users ON users; CREATE TRIGGER trigger_soft_delete_users AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.is_deleted IS DISTINCT FROM NEW.is_deleted) EXECUTE FUNCTION func_soft_delete_users();")
            if control.get("is_users_delete_child_hard", 0):
                catalog["tg"].add("trigger_hard_delete_users")
                await conn.execute("CREATE OR REPLACE FUNCTION func_hard_delete_users() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE r RECORD; BEGIN FOR r IN SELECT table_schema, table_name, column_name FROM information_schema.columns WHERE column_name IN ('created_by_id', 'user_id') AND table_name NOT IN ('users', 'spatial_ref_sys') AND table_schema NOT IN ('information_schema', 'pg_catalog') LOOP EXECUTE format('DELETE FROM %I.%I WHERE %I = $1', r.table_schema, r.table_name, r.column_name) USING OLD.id; END LOOP; RETURN OLD; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_hard_delete_users ON users; CREATE TRIGGER trigger_hard_delete_users AFTER DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_hard_delete_users();")
            if control.get("is_users_delete_disable_role", 0) and "role" in users_cols:
                catalog["tg"].add("trigger_delete_disable_role_users")
                await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_role_users() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.role IS NOT NULL THEN RAISE EXCEPTION 'DELETE not allowed for user with role'; END IF; RETURN OLD; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_delete_disable_role_users ON users; CREATE TRIGGER trigger_delete_disable_role_users BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_delete_disable_role_users();")
        await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_is_protected() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.is_protected=1 THEN RAISE EXCEPTION 'DELETE not allowed for protected row in %', TG_TABLE_NAME; END IF; RETURN OLD; END; $$;")
        await conn.execute("CREATE OR REPLACE FUNCTION func_set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at=NOW(); RETURN NEW; END; $$;")
        await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_bulk() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE n BIGINT := TG_ARGV[0]; BEGIN IF (SELECT COUNT(*) FROM deleted_rows) > n THEN RAISE EXCEPTION 'cant delete more than % rows',n; END IF; RETURN OLD; END; $$;")
        await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_table() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'operation not allowed on %', TG_TABLE_NAME; END; $$;")
        drop_tags = []
        # Note: 'DROP DATABASE' is not supported by event triggers in Postgres
        if is_drop_schema: drop_tags.append("'DROP SCHEMA'")
        if is_drop_table: drop_tags.append("'DROP TABLE'")
        if drop_tags:
            tag_list = ",".join(drop_tags)
            await conn.execute("CREATE OR REPLACE FUNCTION func_drop_disable() RETURNS event_trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'dropping objects is disabled in configuration'; END; $$;")
            await conn.execute("DROP EVENT TRIGGER IF EXISTS trigger_drop_disable")
            await conn.execute(f"CREATE EVENT TRIGGER trigger_drop_disable ON ddl_command_start WHEN TAG IN ({tag_list}) EXECUTE FUNCTION func_drop_disable();")
        else:
            await conn.execute("DROP EVENT TRIGGER IF EXISTS trigger_drop_disable")
        for table, cols in db_tables.items():
            if table == "spatial_ref_sys":
                continue
            if is_truncate_table:
                trunc_tg_name = f"trigger_truncate_disable_{table}"
                catalog["tg"].add(trunc_tg_name)
                await conn.execute(f"DROP TRIGGER IF EXISTS {trunc_tg_name} ON {table}; CREATE TRIGGER {trunc_tg_name} BEFORE TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION func_delete_disable_table();")
            if "is_protected" in cols:
                prot_tg_name = f"trigger_delete_disable_is_protected_{table}"
                catalog["tg"].add(prot_tg_name)
                await conn.execute(f"DROP TRIGGER IF EXISTS {prot_tg_name} ON {table}")
                await conn.execute(f"CREATE TRIGGER {prot_tg_name} BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION func_delete_disable_is_protected();")
            if "updated_at" in cols:
                upd_tg_name = f"trigger_updated_at_set_{table}"
                catalog["tg"].add(upd_tg_name)
                await conn.execute(f"DROP TRIGGER IF EXISTS {upd_tg_name} ON {table}")
                await conn.execute(f"CREATE TRIGGER {upd_tg_name} BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION func_set_updated_at();")
        if table_blocked == ["*"]:
            table_blocked = [t for t in db_tables if t != "spatial_ref_sys"]
        if bulk_blocked and bulk_blocked[0][0] == "*":
            limit = bulk_blocked[0][1]
            bulk_blocked = [[t, limit] for t in db_tables if t != "spatial_ref_sys"]
        for table, limit in bulk_blocked:
            if table in db_tables:
                bulk_tg_name = f"trigger_delete_disable_bulk_{table}"
                catalog["tg"].add(bulk_tg_name)
                await conn.execute(f"DROP TRIGGER IF EXISTS {bulk_tg_name} ON {table}")
                await conn.execute(f"CREATE TRIGGER {bulk_tg_name} AFTER DELETE ON {table} REFERENCING OLD TABLE AS deleted_rows FOR EACH STATEMENT EXECUTE FUNCTION func_delete_disable_bulk({limit});")
        for table in table_blocked:
            if table in db_tables:
                tab_tg_name = f"trigger_delete_disable_{table}"
                catalog["tg"].add(tab_tg_name)
                await conn.execute(f"DROP TRIGGER IF EXISTS {tab_tg_name} ON {table}")
                await conn.execute(f"CREATE TRIGGER {tab_tg_name} BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION func_delete_disable_table();")
        for prefix in ("tg", "uni_chk", "idx"):
            wants = catalog["tg"] if prefix == "tg" else catalog["uni"] | catalog["chk"] if prefix == "uni_chk" else catalog["idx"] | catalog["uni"] | catalog["chk"]
            wants_str = ",".join(f"'{i}'" for i in wants) if wants else "''"
            if prefix == "idx":
                selection = "indexname"
                info_tbl = "pg_indexes"
                join_clause = ""
                drop_fmt = "DROP INDEX IF EXISTS %I"
                drop_vars = "record.indexname"
                like_filter = "(indexname LIKE 'idx_%%' OR indexname LIKE 'unique_%%' OR indexname LIKE 'check_%%')"
            elif prefix == "tg":
                selection = "tgname, relname"
                info_tbl = "pg_trigger"
                join_clause = "JOIN pg_class ON pg_trigger.tgrelid = pg_class.oid"
                drop_fmt = "DROP TRIGGER IF EXISTS %I ON %I"
                drop_vars = "record.tgname, record.relname"
                like_filter = "tgname LIKE 'trigger_%%'"
            else:
                selection = "conname, relname"
                info_tbl = "pg_constraint"
                join_clause = "JOIN pg_class ON pg_constraint.conrelid = pg_class.oid"
                drop_fmt = "ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I"
                drop_vars = "record.relname, record.conname"
                like_filter = "(conname LIKE 'unique_%%' OR conname LIKE 'check_%%')"
            await conn.execute(f"""DO $$ DECLARE record RECORD; BEGIN FOR record IN SELECT {selection} FROM {info_tbl} {join_clause} WHERE {like_filter} LOOP IF NOT record.{selection.split(",")[0]} IN ({wants_str}) THEN EXECUTE format('{drop_fmt}', {drop_vars}); END IF; END LOOP; END $$;""")
        await conn.execute("VACUUM ANALYZE;")
    return "database init done"
