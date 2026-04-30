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

async def func_postgres_serialize(*, client_postgres_pool: any, client_password_hasher: any, cache_postgres_schema: dict, table: str, obj_list: list, is_base: int) -> list:
    """Serialize Python objects (JSON, Arrays, Geog) to PostgreSQL compatible formats using schema-aware injection."""
    output_list = []
    import orjson
    if table not in cache_postgres_schema:
        return obj_list
    schema = cache_postgres_schema[table]
    for item in obj_list:
        new_item = {}
        for col, val in item.items():
            if table == "users" and col == "password" and val:
                val = client_password_hasher.hash(str(val))
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
                        new_item[col] = val
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

async def func_postgres_schema_init(*, client_postgres_pool: any, client_password_hasher: any, config_postgres: dict, config_postgres_root_user_password: str) -> str:
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
        column_names = {col["name"] for col in column_configs if "name" in col}
        for col in column_configs:
            name, dtype = col.get("name"), col.get("datatype")
            if not name or not dtype:
                raise Exception(f"Missing mandatory key 'name' or 'datatype' in {table_name} column: {col}")
            if name.lower() in reserved:
                raise Exception(f"Column name '{name}' in table '{table_name}' is a PostgreSQL reserved keyword. Please rename it.")
            # Regex validation
            if "regex" in col and "[]" in dtype.lower():
                raise Exception(f"Regex constraint is not supported for array column {table_name}.{name}. Remove 'regex' key to resolve.")
            # Index Compatibility & Spatial Enforcement (Refactored for new syntax)
            if col.get("index"):
                for index_group in (x.strip() for x in col["index"].split("|")):
                    if "(" in index_group and index_group.endswith(")"):
                        index_type, cols_str = index_group[:-1].split("(", 1)
                        index_type = index_type.strip().lower()
                        index_cols = [c.strip() for c in cols_str.split(",")]
                        # Validate each column in the index exists
                        for ic in index_cols:
                            if ic not in column_names:
                                raise Exception(f"Index in {table_name} references non-existent column '{ic}'. Defined: {list(column_names)}")
                        if index_type == "gin":
                            if not any(x in dtype.lower() for x in ("[]", "jsonb", "text", "varchar")):
                                raise Exception(f"GIN index is not compatible with '{dtype}' on {table_name}.{name}. Supported: arrays, jsonb, text, varchar.")
                        elif index_type == "gist":
                            if not any(x in dtype.lower() for x in ("geography", "geometry", "box", "circle", "point", "polygon")):
                                raise Exception(f"GIST index is not compatible with '{dtype}' on {table_name}.{name}. Supported: geography, geometry, spatial types.")
                        if any(x in dtype.lower() for x in ("geography", "geometry")) and index_type != "gist":
                            raise Exception(f"Spatial column {table_name}.{name} must use 'gist' index if indexed.")
                    else:
                        raise Exception(f"Invalid index syntax '{index_group}' in {table_name}.{name}. Expected 'col(type)' or 'col1,col2(type)'.")
        for col in column_configs:
            if col.get("unique"):
                for group in col["unique"].split("|"):
                    for u_col in (x.strip() for x in group.split(",") if x.strip()):
                        if u_col not in column_names:
                            raise Exception(f"Unique constraint in {table_name} references non-existent column '{u_col}'. Defined columns: {list(column_names)}")
    import hashlib
    def get_hash(val: str) -> str:
        return hashlib.md5(str(val).encode()).hexdigest()[:4]
    async with client_postgres_pool.acquire() as conn:
        if is_ext:
            extensions = config_postgres.get("extension", [])
            for extension in extensions:
                try:
                    await conn.execute(f"CREATE EXTENSION IF NOT EXISTS {extension};")
                except Exception as e:
                    if any(x in str(e).lower() for x in ("insufficient_privilege", "permission denied", "must be superuser")) or "pg_cron" in extension:
                        print(f"⚠️  {f'extension {extension}':<30} : ❌ skipped (insufficient privileges)")
                    else:
                        raise e
        for table_name, column_configs in config_postgres["table"].items():
            await conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (id BIGSERIAL PRIMARY KEY);")
            if is_autovacuum:
                await conn.execute(f"ALTER TABLE {table_name} SET (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);")
            rows = await conn.fetch("SELECT a.attname, format_type(a.atttypid, a.atttypmod) as type, a.attnotnull as notnull, pg_get_expr(ad.adbin, ad.adrelid) as default FROM pg_attribute a JOIN pg_class t ON a.attrelid = t.oid JOIN pg_namespace n ON t.relnamespace = n.oid LEFT JOIN pg_attrdef ad ON a.attrelid = ad.adrelid AND a.attnum = ad.adnum WHERE t.relname = $1 AND n.nspname = 'public' AND a.attnum > 0 AND NOT a.attisdropped", table_name)
            current_cols = {r[0]: r[1] for r in rows}
            current_notnulls = {r[0]: r[2] for r in rows}
            current_defaults = {r[0]: r[3] for r in rows}
            meta_rows = await conn.fetch("SELECT indexname as name FROM pg_indexes WHERE tablename=$1 UNION ALL SELECT conname as name FROM pg_constraint WHERE conrelid=$1::regclass", table_name)
            existing_meta = {r[0] for r in meta_rows}
            table_changed = False
            # Drop all managed triggers before structural changes to avoid dependency errors (e.g. type changes on columns used in triggers)
            await conn.execute(f"DO $$ DECLARE r RECORD; BEGIN FOR r IN SELECT tgname FROM pg_trigger JOIN pg_class ON pg_trigger.tgrelid = pg_class.oid WHERE relname = '{table_name}' AND tgname LIKE 'trigger_%%' LOOP EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I', r.tgname, '{table_name}'); END LOOP; END $$;")
            for col_cfg in column_configs:
                col_name = col_cfg["name"]
                col_type = col_cfg["datatype"]
                if col_name not in current_cols:
                    old_name = col_cfg.get("old")
                    if old_name and old_name in current_cols:
                        await conn.execute(f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {col_name}")
                        current_cols[col_name] = current_cols.pop(old_name)
                        current_notnulls[col_name] = current_notnulls.pop(old_name)
                        table_changed = True
                    else:
                        default_val = f"""DEFAULT {col_cfg["default"]}""" if "default" in col_cfg else ""
                        mandatory_val = "NOT NULL" if col_cfg.get("is_mandatory") == 1 else ""
                        await conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {default_val} {mandatory_val}")
                        current_cols[col_name] = col_type.split("(")[0].lower()
                        current_notnulls[col_name] = (col_cfg.get("is_mandatory") == 1)
                        table_changed = True
                else:
                    type_mapping = {"timestamp with time zone": "timestamptz", "character varying": "varchar", "integer": "int", "boolean": "bool"}
                    current_type = type_mapping.get(current_cols[col_name].lower().split("(")[0], current_cols[col_name].lower().split("(")[0])
                    target_type = type_mapping.get(col_type.lower().split("(")[0], col_type.lower().split("(")[0])
                    if type_mapping.get(current_cols[col_name].lower().split("(")[0], current_cols[col_name].lower().split("(")[0]) != type_mapping.get(col_type.lower().split("(")[0], col_type.lower().split("(")[0]):
                        await conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} TYPE {col_type} USING {col_name}::{col_type}")
                        table_changed = True
                    target_notnull = (col_cfg.get("is_mandatory") == 1)
                    if current_notnulls[col_name] != target_notnull:
                        if target_notnull:
                            await conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} SET NOT NULL")
                        else:
                            await conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} DROP NOT NULL")
                        table_changed = True
                    target_default = str(col_cfg.get("default")).strip() if "default" in col_cfg else None
                    current_default = current_defaults.get(col_name)
                    if target_default:
                        if current_default is None or target_default not in current_default:
                             await conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} SET DEFAULT {target_default}")
                             table_changed = True
                    elif current_default is not None:
                        await conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} DROP DEFAULT")
                        table_changed = True
            # 3. Sync Indexes & Constraints (Logic-Aware)
            for col_cfg in column_configs:
                col_name = col_cfg["name"]
                col_type = col_cfg["datatype"]
                if col_cfg.get("index"):
                    for index_group in (x.strip() for x in col_cfg["index"].split("|")):
                        if "(" in index_group and index_group.endswith(")"):
                            index_type, cols_str = index_group[:-1].split("(", 1)
                            index_type = index_type.strip().lower()
                            index_cols = [c.strip() for c in cols_str.split(",")]
                            idx_name = f"idx_{table_name}_{'_'.join(index_cols)}_{index_type}"
                            catalog["idx"].add(idx_name)
                            if idx_name not in existing_meta:
                                # Apply trigram ops if it's a single-column GIN index on text
                                ops = ""
                                if index_type == "gin" and len(index_cols) == 1:
                                    # We use the current col_type if the index is on the current column
                                    if index_cols[0] == col_name and "text" in col_type.lower() and "[]" not in col_type.lower():
                                        ops = "gin_trgm_ops"
                                cols_joined = ", ".join(index_cols)
                                if ops:
                                    await conn.execute(f"CREATE INDEX {idx_name} ON {table_name} USING {index_type}({index_cols[0]} {ops});")
                                else:
                                    await conn.execute(f"CREATE INDEX {idx_name} ON {table_name} USING {index_type}({cols_joined});")
                                table_changed = True
                if "in" in col_cfg:
                    chk_name = f"check_{table_name}_{col_name}_in_{get_hash(col_cfg['in'])}"
                    catalog["chk"].add(chk_name)
                    if chk_name not in existing_meta:
                        await conn.execute(f"""ALTER TABLE {table_name} ADD CONSTRAINT {chk_name} CHECK ({col_name} IN {col_cfg["in"]});""")
                        table_changed = True
                if "regex" in col_cfg:
                    regex_name = f"check_{table_name}_{col_name}_regex_{get_hash(col_cfg['regex'])}"
                    catalog["chk"].add(regex_name)
                    if regex_name not in existing_meta:
                        await conn.execute(f"""ALTER TABLE {table_name} ADD CONSTRAINT {regex_name} CHECK ({col_name} ~ '{col_cfg["regex"]}');""")
                        table_changed = True
                if "check" in col_cfg:
                    vld_name = f"check_{table_name}_{col_name}_vld_{get_hash(col_cfg['check'])}"
                    catalog["chk"].add(vld_name)
                    if vld_name not in existing_meta:
                        await conn.execute(f"""ALTER TABLE {table_name} ADD CONSTRAINT {vld_name} CHECK ({col_cfg["check"]});""")
                        table_changed = True
                if col_cfg.get("unique"):
                    for group in col_cfg["unique"].split("|"):
                        unique_cols = [x.strip() for x in group.split(",")]
                        uni_name = f"""unique_{table_name}_{"_".join(unique_cols)}"""
                        catalog["uni"].add(uni_name)
                        if uni_name not in existing_meta:
                            await conn.execute(f"""ALTER TABLE {table_name} ADD CONSTRAINT {uni_name} UNIQUE ({",".join(unique_cols)});""")
                            table_changed = True
            # Targeted Analyze ONLY if table structural changes occurred
            if table_changed:
                await conn.execute(f"ANALYZE {table_name};")
        db_schema_rows = await conn.fetch("SELECT c.table_name, c.column_name FROM information_schema.columns c JOIN information_schema.tables t ON c.table_name = t.table_name AND c.table_schema = t.table_schema WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE'")
        db_tables = {}
        for row in db_schema_rows:
            db_tables.setdefault(row[0], []).append(row[1])
        users_cols = db_tables.get("users", [])
        if users_cols:
            catalog["tg"].add("trigger_no_delete_root_users")
            await conn.execute("CREATE OR REPLACE FUNCTION func_no_delete_root_users() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.id = 1 THEN RAISE EXCEPTION 'DELETE not allowed for root user (id=1)'; END IF; RETURN OLD; END; $$; DROP TRIGGER IF EXISTS trigger_no_delete_root_users ON users; CREATE TRIGGER trigger_no_delete_root_users BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_no_delete_root_users();")
            if all(c in users_cols for c in ("type", "username", "password", "role", "is_active")):
                root_user_password_hash = client_password_hasher.hash(config_postgres_root_user_password)
                await conn.execute("INSERT INTO users (id, type, username, password, role, is_active) VALUES (1, 1, 'atom', $1, 1, 1) ON CONFLICT (id) DO UPDATE SET type = EXCLUDED.type, username = EXCLUDED.username, role = 1, is_active = 1 WHERE users.type IS DISTINCT FROM 1 OR users.username IS DISTINCT FROM EXCLUDED.username OR users.role IS DISTINCT FROM 1 OR users.is_active IS DISTINCT FROM 1;", root_user_password_hash)
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
        if is_drop_schema: drop_tags.append("'DROP SCHEMA'")
        if is_drop_table: drop_tags.append("'DROP TABLE'")
        if drop_tags:
            tag_list = ",".join(drop_tags)
            await conn.execute("CREATE OR REPLACE FUNCTION func_drop_disable() RETURNS event_trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'dropping objects is disabled in configuration'; END; $$;")
            try:
                await conn.execute("DROP EVENT TRIGGER IF EXISTS trigger_drop_disable")
                await conn.execute(f"CREATE EVENT TRIGGER trigger_drop_disable ON ddl_command_start WHEN TAG IN ({tag_list}) EXECUTE FUNCTION func_drop_disable();")
            except Exception as e:
                if any(x in str(e).lower() for x in ("insufficient_privilege", "permission denied", "must be superuser")):
                    print(f"⚠️  {'event trigger':<30} : ❌ skipped (insufficient privileges)")
                else:
                    raise e
        else:
            try:
                await conn.execute("DROP EVENT TRIGGER IF EXISTS trigger_drop_disable")
            except:
                pass
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
        managed_tables = list(config_postgres["table"].keys())
        managed_tables_str = ",".join(f"'{t}'" for t in managed_tables) if managed_tables else "''"
        for prefix in ("tg", "uni_chk", "idx"):
            wants = catalog["tg"] if prefix == "tg" else catalog["uni"] | catalog["chk"] if prefix == "uni_chk" else catalog["idx"] | catalog["uni"] | catalog["chk"]
            wants_str = ",".join(f"'{i}'" for i in wants) if wants else "''"
            if prefix == "idx":
                selection = "indexname"
                info_tbl = "pg_indexes"
                join_clause = ""
                drop_fmt = "DROP INDEX IF EXISTS %I"
                drop_vars = "record.indexname"
                like_filter = f"(indexname LIKE 'idx_%%' OR indexname LIKE 'unique_%%' OR indexname LIKE 'check_%%') AND tablename IN ({managed_tables_str})"
            elif prefix == "tg":
                selection = "tgname, relname"
                info_tbl = "pg_trigger"
                join_clause = "JOIN pg_class ON pg_trigger.tgrelid = pg_class.oid"
                drop_fmt = "DROP TRIGGER IF EXISTS %I ON %I"
                drop_vars = "record.tgname, record.relname"
                like_filter = f"tgname LIKE 'trigger_%%' AND relname IN ({managed_tables_str})"
            else:
                selection = "conname, relname"
                info_tbl = "pg_constraint"
                join_clause = "JOIN pg_class ON pg_constraint.conrelid = pg_class.oid"
                drop_fmt = "ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I"
                drop_vars = "record.relname, record.conname"
                like_filter = f"(conname LIKE 'unique_%%' OR conname LIKE 'check_%%') AND relname IN ({managed_tables_str})"
            await conn.execute(f"""DO $$ DECLARE record RECORD; BEGIN FOR record IN SELECT {selection} FROM {info_tbl} {join_clause} WHERE {like_filter} LOOP IF NOT record.{selection.split(",")[0]} IN ({wants_str}) THEN EXECUTE format('{drop_fmt}', {drop_vars}); END IF; END LOOP; END $$;""")
    print(f"🏗️  {'postgres schema sync':<30} : ✅ done")
    return "database init done"
