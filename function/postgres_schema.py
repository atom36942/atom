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
    
async def func_postgres_schema_init(*, client_postgres_pool: any, config_postgres: dict) -> str:
    """Initialize PostgreSQL database schema, tables, indexes, constraints, and triggers based on configuration."""
    if not config_postgres:
        raise Exception("config_postgres missing")
    if "table" not in config_postgres:
        raise Exception("config_postgres.table missing")
    control = config_postgres.get("control", {})
    is_ext = control.get("is_extension", 0)
    is_match = control.get("is_column_match", 0)
    bulk_blocked = control.get("table_row_delete_disable_bulk", [])
    table_blocked = control.get("table_row_delete_disable", [])
    is_autovacuum = control.get("is_autovacuum_optimize", 0)
    is_analyze = control.get("is_analyze_init", 0)
    catalog = {"idx": set(), "uni": set(), "chk": set(), "tg": set()}
    for table_name, column_configs in config_postgres["table"].items():
        column_names = [col["name"] for col in column_configs]
        if len(set(column_names)) != len(column_configs):
            raise Exception(f"Duplicate column in {table_name}")
    async with client_postgres_pool.acquire() as conn:
        if is_ext:
            for extension in ("postgis", "pg_trgm", "btree_gin"):
                await conn.execute(f"CREATE EXTENSION IF NOT EXISTS {extension};")
        for table_name, column_configs in config_postgres["table"].items():
            await conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} (id BIGSERIAL PRIMARY KEY);")
            if is_autovacuum:
                await conn.execute(f"ALTER TABLE {table_name} SET (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);")
            current_cols = {row[0]: row[1] for row in await conn.fetch("SELECT a.attname, format_type(a.atttypid, a.atttypmod) FROM pg_attribute a JOIN pg_class t ON a.attrelid = t.oid JOIN pg_namespace n ON t.relnamespace = n.oid WHERE t.relname = $1 AND n.nspname = 'public' AND a.attnum > 0 AND NOT a.attisdropped", table_name)}
            for col_cfg in column_configs:
                col_name = col_cfg["name"]
                col_type = col_cfg["datatype"]
                if col_name not in current_cols:
                    old_name = col_cfg.get("old")
                    if old_name and old_name in current_cols:
                        await conn.execute(f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {col_name}")
                        current_cols[col_name] = current_cols.pop(old_name)
                    else:
                        default_val = f"""DEFAULT {col_cfg["default"]}""" if "default" in col_cfg else ""
                        await conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {default_val}")
                        current_cols[col_name] = col_type.split("(")[0].lower()
                else:
                    type_mapping = {"timestamp with time zone": "timestamptz", "character varying": "varchar", "integer": "int", "boolean": "bool"}
                    current_type = type_mapping.get(current_cols[col_name].lower().split("(")[0], current_cols[col_name].lower().split("(")[0])
                    target_type = type_mapping.get(col_type.lower().split("(")[0], col_type.lower().split("(")[0])
                    if current_type != target_type:
                        if is_match:
                            await conn.execute(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} TYPE {col_type} USING {col_name}::{col_type}")
                        else:
                            raise Exception(f"Type mismatch {table_name}.{col_name}: {current_cols[col_name]} vs {col_type}")
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
                if col_cfg.get("unique"):
                    for group in col_cfg["unique"].split("|"):
                        unique_cols = [x.strip() for x in group.split(",")]
                        uni_name = f"""unique_{table_name}_{"_".join(unique_cols)}"""
                        catalog["uni"].add(uni_name)
                        await conn.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {uni_name}")
                        await conn.execute(f"""ALTER TABLE {table_name} ADD CONSTRAINT {uni_name} UNIQUE ({",".join(unique_cols)});""")
            if is_match:
                configured_cols = {cfg["name"] for cfg in column_configs} | {"id"}
                for col_to_drop in set(current_cols.keys()) - configured_cols:
                    await conn.execute(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {col_to_drop} CASCADE;")
        db_schema_rows = await conn.fetch("SELECT c.table_name, c.column_name FROM information_schema.columns c JOIN information_schema.tables t ON c.table_name = t.table_name AND c.table_schema = t.table_schema WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE'")
        db_tables = {}
        for row in db_schema_rows:
            db_tables.setdefault(row[0], []).append(row[1])
        users_cols = db_tables.get("users", [])
        if users_cols:
            catalog["tg"].add("trigger_users_root_no_delete")
            await conn.execute("CREATE OR REPLACE FUNCTION func_users_root_no_delete() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.id = 1 THEN RAISE EXCEPTION 'DELETE not allowed for root user (id=1)'; END IF; RETURN OLD; END; $$; DROP TRIGGER IF EXISTS trigger_users_root_no_delete ON users; CREATE TRIGGER trigger_users_root_no_delete BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_users_root_no_delete();")
            if all(c in users_cols for c in ("type", "username", "password", "role", "is_active")):
                root_user_password = control.get("root_user_password", "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3")
                await conn.execute("INSERT INTO users (type, username, password, role, is_active) VALUES (1, 'atom', $1, 1, 1) ON CONFLICT (username, type) DO UPDATE SET password = EXCLUDED.password, role = EXCLUDED.role, is_active = EXCLUDED.is_active;", root_user_password)
            if "password" in users_cols and "log_users_password" in db_tables:
                catalog["tg"].add("trigger_users_password_log")
                await conn.execute("CREATE OR REPLACE FUNCTION func_users_password_log() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.password IS DISTINCT FROM NEW.password THEN INSERT INTO log_users_password (user_id, password) VALUES (NEW.id, NEW.password); END IF; RETURN NEW; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_users_password_log ON users; CREATE TRIGGER trigger_users_password_log AFTER UPDATE ON users FOR EACH ROW EXECUTE FUNCTION func_users_password_log();")
            if control.get("is_users_child_delete_soft", 0) and "is_deleted" in users_cols:
                catalog["tg"].add("trigger_users_soft_delete")
                await conn.execute("CREATE OR REPLACE FUNCTION func_users_soft_delete() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE r RECORD; v INTEGER; BEGIN v := (CASE WHEN NEW.is_deleted=1 THEN 1 ELSE NULL END); FOR r IN SELECT table_schema, table_name, column_name FROM information_schema.columns WHERE column_name IN ('created_by_id', 'user_id') AND table_name NOT IN ('users', 'spatial_ref_sys') AND table_schema NOT IN ('information_schema', 'pg_catalog') LOOP IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = r.table_schema AND table_name = r.table_name AND column_name = 'is_deleted') THEN EXECUTE format('UPDATE %I.%I SET is_deleted = $1 WHERE %I = $2', r.table_schema, r.table_name, r.column_name) USING v, NEW.id; END IF; END LOOP; RETURN NEW; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_users_soft_delete ON users; CREATE TRIGGER trigger_users_soft_delete AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.is_deleted IS DISTINCT FROM NEW.is_deleted) EXECUTE FUNCTION func_users_soft_delete();")
            if control.get("is_users_child_delete_hard", 0):
                catalog["tg"].add("trigger_users_hard_delete")
                await conn.execute("CREATE OR REPLACE FUNCTION func_users_hard_delete() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE r RECORD; BEGIN FOR r IN SELECT table_schema, table_name, column_name FROM information_schema.columns WHERE column_name IN ('created_by_id', 'user_id') AND table_name NOT IN ('users', 'spatial_ref_sys') AND table_schema NOT IN ('information_schema', 'pg_catalog') LOOP EXECUTE format('DELETE FROM %I.%I WHERE %I = $1', r.table_schema, r.table_name, r.column_name) USING OLD.id; END LOOP; RETURN OLD; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_users_hard_delete ON users; CREATE TRIGGER trigger_users_hard_delete AFTER DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_users_hard_delete();")
            if control.get("is_users_delete_disable_role", 0) and "role" in users_cols:
                catalog["tg"].add("trigger_delete_disable_users_role")
                await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_users_role() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.role IS NOT NULL THEN RAISE EXCEPTION 'DELETE not allowed for user with role'; END IF; RETURN OLD; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_delete_disable_users_role ON users; CREATE TRIGGER trigger_delete_disable_users_role BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_delete_disable_users_role();")
        await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_is_protected() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.is_protected=1 THEN RAISE EXCEPTION 'DELETE not allowed for protected row in %', TG_TABLE_NAME; END IF; RETURN OLD; END; $$;")
        await conn.execute("CREATE OR REPLACE FUNCTION func_set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at=NOW(); RETURN NEW; END; $$;")
        await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_bulk() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE n BIGINT := TG_ARGV[0]; BEGIN IF (SELECT COUNT(*) FROM deleted_rows) > n THEN RAISE EXCEPTION 'cant delete more than % rows',n; END IF; RETURN OLD; END; $$;")
        await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_table() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'delete not allowed on %', TG_TABLE_NAME; END; $$;")
        for table, cols in db_tables.items():
            if table == "spatial_ref_sys":
                continue
            if "is_protected" in cols:
                prot_tg_name = f"trigger_delete_disable_is_protected_{table}"
                catalog["tg"].add(prot_tg_name)
                await conn.execute(f"DROP TRIGGER IF EXISTS {prot_tg_name} ON {table}")
                await conn.execute(f"CREATE TRIGGER {prot_tg_name} BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION func_delete_disable_is_protected();")
            if "updated_at" in cols:
                upd_tg_name = f"trigger_set_updated_at_{table}"
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
            wants_str = ",".join(f"'{i}'" for i in wants) if wants else "NULL"
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
        if is_analyze:
            await conn.execute("ANALYZE;")
    return "database init done"