def func_check(*, app: any) -> None:
    """Validate config_api entries against registered routes and middleware config formats."""
    config_api = getattr(app.state, "config_api", {})
    if not isinstance(config_api, dict): raise Exception("config_api must be dict")
    route_paths = {route.path for route in app.routes if hasattr(route, "path")}
    api_ids = []
    user_mode_allowed = ("redis", "realtime", "inmemory", "token")
    api_mode_allowed = ("redis", "inmemory")
    api_keys_allowed = ("id", "is_token", "user_check_role", "user_check_deactivated", "user_check_deleted", "api_cache_sec", "api_ratelimiting_times_sec")
    def flag_check(value, key):
        if value not in (0, 1, "0", "1", True, False): raise Exception(f"invalid {key}: expected 0/1")
    def int_check(value, key, min_value=0):
        try:
            value = int(value)
        except Exception:
            raise Exception(f"invalid {key}: expected integer")
        if value < min_value: raise Exception(f"invalid {key}: minimum {min_value}")
        return value
    def mode_list_check(path, cfg, key, allowed_mode, min_len, max_len):
        if key not in cfg: return ()
        value = cfg[key]
        if isinstance(value, str): value = [value]
        if not isinstance(value, list): raise Exception(f"{path} invalid {key}: expected list")
        if len(value) < min_len or len(value) > max_len: raise Exception(f"{path} invalid {key}: expected {min_len}-{max_len} values")
        if value[0] not in allowed_mode: raise Exception(f"{path} invalid {key} mode: {value[0]}, allowed: {', '.join(allowed_mode)}")
        return value
    requires_redis = False
    requires_redis_ratelimiter = False
    for path, cfg in config_api.items():
        if not isinstance(path, str) or not path.startswith("/"): raise Exception(f"invalid config_api path: {path}")
        if path not in route_paths: raise Exception(f"unused configuration in config_api: {path} (route not found)")
        if not isinstance(cfg, dict): raise Exception(f"{path} config must be dict")
        for key in cfg.keys():
            if key not in api_keys_allowed: raise Exception(f"{path} invalid config key: {key}")
        if "id" not in cfg: raise Exception(f"{path} missing required key: id")
        api_id = int_check(cfg["id"], f"{path} id", 1)
        if api_id in api_ids: raise Exception(f"duplicate api id: {api_id}")
        api_ids.append(api_id)
        if "is_token" not in cfg: raise Exception(f"{path} missing required key: is_token")
        flag_check(cfg["is_token"], f"{path} is_token")
        role_cfg = mode_list_check(path, cfg, "user_check_role", user_mode_allowed, 2, 2)
        if role_cfg:
            if not isinstance(role_cfg[1], list) or not role_cfg[1]: raise Exception(f"{path} invalid user_check_role roles")
            for role in role_cfg[1]: int_check(role, f"{path} user_check_role role", 1)
            if role_cfg[0] == "redis": requires_redis = True
        for key in ("user_check_deactivated", "user_check_deleted"):
            user_cfg = mode_list_check(path, cfg, key, user_mode_allowed, 1, 1)
            if user_cfg:
                if user_cfg[0] == "redis": requires_redis = True
        cache_cfg = mode_list_check(path, cfg, "api_cache_sec", api_mode_allowed, 3, 3)
        if cache_cfg:
            ttl = int_check(cache_cfg[1], f"{path} api_cache_sec ttl", 1)
            if ttl > 315360000: raise Exception(f"{path} api_cache_sec ttl exceeds 10 years")
            flag_check(cache_cfg[2], f"{path} api_cache_sec user flag")
            if cache_cfg[0] == "redis": requires_redis = True
        rate_cfg = mode_list_check(path, cfg, "api_ratelimiting_times_sec", api_mode_allowed, 3, 3)
        if rate_cfg:
            int_check(rate_cfg[1], f"{path} api_ratelimiting_times_sec limit", 1)
            window = int_check(rate_cfg[2], f"{path} api_ratelimiting_times_sec window", 1)
            if window > 31536000: raise Exception(f"{path} api_ratelimiting_times_sec window exceeds 1 year")
            if rate_cfg[0] == "redis": requires_redis_ratelimiter = True
    for path in route_paths:
        if path not in config_api:
            raise Exception(f"CRITICAL: Route '{path}' is missing from config_api. All routes must be explicitly configured.")
    if requires_redis and not getattr(app.state, "config_redis_url", None):
        raise Exception("config_api uses redis mode but config_redis_url is missing")
    if requires_redis_ratelimiter and not getattr(app.state, "config_redis_url_ratelimiter", None):
        raise Exception("config_api uses redis rate limiting but config_redis_url_ratelimiter is missing")

    buffer_limit = getattr(app.state, "config_buffer_limit_default", None)
    if buffer_limit is not None:
        if not isinstance(buffer_limit, int) or buffer_limit < 10 or buffer_limit > 5000:
            raise Exception("config_buffer_limit_default must be an integer between 10 and 5000")
            
    return None

async def func_postgres_schema_init(*, client_postgres: any, config_postgres: dict, root_user_password_hash: str = None) -> str:
    """Initialize PostgreSQL database schema, tables, indexes, constraints, and triggers based on configuration."""
    config_db = config_postgres
    if not config_db: raise Exception("config_db missing")
    if "table" not in config_db: raise Exception("config_db.table missing")
    control = config_db.get("control", {})
    def get_enable_control_switch(key: str, default: int = 1, legacy_disable_keys: tuple = ()) -> int:
        if key in control:
            return control.get(key)
        for legacy_key in legacy_disable_keys:
            if legacy_key in control:
                return 0 if control.get(legacy_key) else 1
        return default
    is_autovacuum = control.get("is_enable_autovacuum_optimize", 0)
    is_enable_drop_schema = get_enable_control_switch("is_enable_drop_schema", 1, ("is_enable_drop_schema_disable", "is_disable_drop_schema"))
    is_enable_drop_table = get_enable_control_switch("is_enable_drop_table", 1, ("is_enable_drop_table_disable", "is_disable_drop_table"))
    is_enable_truncate_table = get_enable_control_switch("is_enable_truncate_table", 1, ("is_enable_truncate_disable", "is_disable_truncate"))
    is_enable_drop_column = get_enable_control_switch("is_enable_drop_column", 0, ("is_enable_drop_column_disable", "is_disable_drop_column"))
    is_enable_root_user_delete_disable = control.get("is_enable_root_user_delete_disable", control.get("is_enable_users_protect_root", 1))
    is_enable_root_user_create = control.get("is_enable_root_user_create", 1)
    is_enable_log_users_password = control.get("is_enable_log_users_password", 1)
    is_enable_log_users_delete = control.get("is_enable_log_users_delete", 1)
    is_enable_is_protected_delete_disable = control.get("is_enable_is_protected_delete_disable", 1)
    is_enable_updated_at_set = control.get("is_enable_updated_at_set", 1)
    is_enable_users_role_delete_disable_hard = control.get("is_enable_users_role_delete_disable_hard", control.get("is_enable_users_protect_role", control.get("is_enable_users_protect_with_role", 0 if control.get("is_enable_users_delete_with_role", control.get("is_enable_users_delete_role", 1)) else 1)))
    is_enable_users_role_delete_disable_soft = control.get("is_enable_users_role_delete_disable_soft", 0)
    if "is_enable_users_delete_role_disable" in control:
        is_enable_users_role_delete_disable_hard = control.get("is_enable_users_delete_role_disable")
    if "is_disable_users_delete_role" in control:
        is_enable_users_role_delete_disable_hard = control.get("is_disable_users_delete_role")
    is_enable_drop_column_mismatch = control.get("is_enable_drop_column_mismatch", control.get("is_drop_column_mismatch_db", control.get("is_drop_column_mismatch", 0)))
    if not is_enable_drop_column and is_enable_drop_column_mismatch:
        raise Exception("config_db.control conflict: is_enable_drop_column=0 blocks is_enable_drop_column_mismatch=1")
    bulk_blocked = control.get("table_row_delete_disable_bulk", control.get("table_delete_disable_row_bulk", control.get("disable_table_delete_row_bulk", [])))
    table_blocked = control.get("table_row_delete_disable_all", control.get("table_delete_disable_row", control.get("disable_table_delete_row", [])))
    catalog = {"idx": set(), "uni": set(), "chk": set(), "tg": set()}
    def register_sql_catalog(sql_config: any) -> None:
        if not isinstance(sql_config, dict):
            return None
        for key, val in sql_config.items():
            if isinstance(key, str) and isinstance(val, str):
                if key.startswith("index_"):
                    catalog["idx"].add(key[6:])
                elif key.startswith("idx_"):
                    catalog["idx"].add(key)
                elif key.startswith("unique_"):
                    catalog["uni"].add(key)
                elif key.startswith("check_"):
                    catalog["chk"].add(key)
            elif isinstance(val, dict):
                register_sql_catalog(val)
        return None
    def iter_sql_queries(sql_config: any):
        if isinstance(sql_config, dict):
            for val in sql_config.values():
                yield from iter_sql_queries(val)
        elif isinstance(sql_config, (list, tuple)):
            for val in sql_config:
                yield from iter_sql_queries(val)
        elif isinstance(sql_config, str) and sql_config.strip():
            yield sql_config
    register_sql_catalog(config_db.get("sql", {}))
    reserved = {"all", "analyze", "and", "any", "as", "asc", "asymmetric", "authorization", "binary", "both", "case", "cast", "check", "collate", "collation", "column", "concurrently", "constraint", "create", "cross", "current_catalog", "current_date", "current_role", "current_schema", "current_time", "current_timestamp", "current_user", "default", "deferrable", "desc", "distinct", "do", "else", "end", "except", "false", "fetch", "for", "foreign", "freeze", "from", "full", "grant", "group", "having", "ilike", "in", "initially", "inner", "intersect", "into", "is", "isnull", "join", "lateral", "leading", "left", "like", "limit", "localtime", "localtimestamp", "natural", "not", "notnull", "null", "offset", "on", "only", "or", "order", "outer", "overlaps", "placing", "primary", "references", "returning", "right", "select", "session_user", "similar", "some", "symmetric", "table", "tablesample", "then", "to", "trailing", "true", "union", "unique", "user", "using", "variadic", "verbose", "when", "where", "window", "with"}
    for table_name, column_configs in config_db["table"].items():
        primary_cfg = column_configs[0] if column_configs else {}
        if len(primary_cfg) > 3:
            raise Exception(f"{table_name}.id primary column config cannot have more than 3 keys")
        if primary_cfg != {"name": "id", "datatype": "bigserial", "is_primary": 1}:
            raise Exception(f"{table_name} first column must be exactly {{'name':'id','datatype':'bigserial','is_primary':1}}")
        for col in column_configs[1:]:
            if col.get("is_primary") == 1:
                raise Exception(f"{table_name} can only define one primary column")
            if col.get("name") == "id":
                raise Exception(f"{table_name}.id must only be defined as the first primary column")
        column_names = set()
        for col in column_configs:
            col_name = col.get("name")
            if col_name:
                if col_name in column_names:
                    raise Exception(f"Duplicate column '{col_name}' defined in table '{table_name}'")
                column_names.add(col_name)
        for col in column_configs:
            name, dtype = col.get("name"), col.get("datatype")
            if not name or not dtype:
                raise Exception(f"Missing mandatory key 'name' or 'datatype' in {table_name} column: {col}")
            if name.lower() in reserved:
                raise Exception(f"Column name '{name}' in table '{table_name}' is a PostgreSQL reserved keyword. Please rename it.")
            if "regex" in col and "[]" in dtype.lower():
                raise Exception(f"Regex constraint is not supported for array column {table_name}.{name}. Remove 'regex' key to resolve.")
            if col.get("index"):
                for index_group in (x.strip() for x in col["index"].split("|")):
                    if "(" in index_group and index_group.endswith(")"):
                        index_type, cols_str = index_group[:-1].split("(", 1)
                        index_type = index_type.strip().lower()
                        index_cols = [c.strip() for c in cols_str.split(",")]
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
    def clamp_identifier(name: str) -> str:
        if len(name) <= 63:
            return name
        return f"{name[:58]}_{get_hash(name)}"
    def is_enabled_col_setting(col_cfg: dict, key: str) -> bool:
        return key in col_cfg and col_cfg.get(key) not in (None, "")
    async with client_postgres.acquire() as conn:
        extensions = config_db.get("extension") or []
        if extensions:
            for extension in extensions:
                try:
                    is_extension_exists = await conn.fetchval("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = $1)", extension)
                    if not is_extension_exists:
                        await conn.execute(f'CREATE EXTENSION "{extension}";')
                except Exception as e:
                    if any(x in str(e).lower() for x in ("insufficient_privilege", "permission denied", "must be superuser")) or "pg_cron" in extension:
                        print(f"⚠️  {f'extension {extension}':<30} : ❌ skipped (insufficient privileges)")
                    else:
                        raise e
        try:
            if not is_enable_drop_column:
                await conn.execute("CREATE OR REPLACE FUNCTION func_drop_column_disable() RETURNS event_trigger LANGUAGE plpgsql AS $$ DECLARE obj RECORD; BEGIN FOR obj IN SELECT * FROM pg_event_trigger_dropped_objects() LOOP IF obj.object_type = 'table column' THEN RAISE EXCEPTION 'dropping columns is disabled in configuration'; END IF; END LOOP; END; $$;")
                await conn.execute("DROP EVENT TRIGGER IF EXISTS trigger_drop_column_disable")
                await conn.execute("CREATE EVENT TRIGGER trigger_drop_column_disable ON sql_drop WHEN TAG IN ('ALTER TABLE') EXECUTE FUNCTION func_drop_column_disable();")
            else:
                await conn.execute("DROP EVENT TRIGGER IF EXISTS trigger_drop_column_disable")
        except Exception as e:
            if any(x in str(e).lower() for x in ("insufficient_privilege", "permission denied", "must be superuser")):
                print(f"⚠️  {'drop column event trigger':<30} : ❌ skipped (insufficient privileges)")
            else:
                raise e
        for table_name, column_configs in config_db["table"].items():
            primary_cfg = column_configs[0]
            await conn.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ("{primary_cfg["name"]}" {primary_cfg["datatype"]} PRIMARY KEY);')
            if is_autovacuum:
                await conn.execute(f'ALTER TABLE "{table_name}" SET (autovacuum_vacuum_scale_factor = 0.05, autovacuum_analyze_scale_factor = 0.02);')
            rows = await conn.fetch("SELECT a.attname, format_type(a.atttypid, a.atttypmod) as type, a.attnotnull as notnull, pg_get_expr(ad.adbin, ad.adrelid) as default FROM pg_attribute a JOIN pg_class t ON a.attrelid = t.oid JOIN pg_namespace n ON t.relnamespace = n.oid LEFT JOIN pg_attrdef ad ON a.attrelid = ad.adrelid AND a.attnum = ad.adnum WHERE t.relname = $1 AND n.nspname = 'public' AND a.attnum > 0 AND NOT a.attisdropped", table_name)
            current_cols = {r[0]: r[1] for r in rows}
            current_notnulls = {r[0]: r[2] for r in rows}
            current_defaults = {r[0]: r[3] for r in rows}
            meta_rows = await conn.fetch("SELECT indexname as name FROM pg_indexes WHERE tablename=$1 UNION ALL SELECT conname as name FROM pg_constraint WHERE conrelid=$1::regclass", table_name)
            existing_meta = {r[0] for r in meta_rows}
            table_changed = False
            await conn.execute(f"DO $$ DECLARE r RECORD; BEGIN FOR r IN SELECT tgname FROM pg_trigger JOIN pg_class ON pg_trigger.tgrelid = pg_class.oid WHERE relname = '{table_name}' AND tgname LIKE 'trigger_%%' LOOP EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I', r.tgname, '{table_name}'); END LOOP; END $$;")
            renamed_cols = {}
            for col_cfg in column_configs:
                if col_cfg.get("is_primary") == 1:
                    continue
                col_name = col_cfg["name"]
                col_type = col_cfg["datatype"]
                if col_name not in current_cols:
                    old_name = col_cfg.get("old") if col_cfg.get("old") not in (None, "") else None
                    if old_name and old_name in current_cols:
                        await conn.execute(f'ALTER TABLE "{table_name}" RENAME COLUMN "{old_name}" TO "{col_name}"')
                        current_cols[col_name] = current_cols.pop(old_name)
                        current_notnulls[col_name] = current_notnulls.pop(old_name)
                        renamed_cols[col_name] = old_name
                        table_changed = True
                    else:
                        default_val = f"""DEFAULT {col_cfg["default"]}""" if is_enabled_col_setting(col_cfg, "default") else ""
                        mandatory_val = "NOT NULL" if col_cfg.get("is_mandatory") == 1 else ""
                        await conn.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type} {default_val} {mandatory_val}')
                        current_cols[col_name] = col_type.split("(")[0].lower()
                        current_notnulls[col_name] = (col_cfg.get("is_mandatory") == 1)
                        table_changed = True
                else:
                    type_map = {"timestamp with time zone": "timestamptz", "character varying": "varchar", "integer": "int", "boolean": "bool"}
                    current_type = type_map.get(current_cols[col_name].lower().split("(")[0], current_cols[col_name].lower().split("(")[0])
                    target_type = type_map.get(col_type.lower().split("(")[0], col_type.lower().split("(")[0])
                    if current_type != target_type:
                        await conn.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN "{col_name}" TYPE {col_type} USING "{col_name}"::{col_type}')
                        table_changed = True
                    target_notnull = (col_cfg.get("is_mandatory") == 1)
                    if current_notnulls[col_name] != target_notnull:
                        if target_notnull:
                            await conn.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN "{col_name}" SET NOT NULL')
                        else:
                            await conn.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN "{col_name}" DROP NOT NULL')
                        table_changed = True
                    target_default = str(col_cfg.get("default")).strip() if is_enabled_col_setting(col_cfg, "default") else None
                    current_default = current_defaults.get(col_name)
                    if target_default:
                        if current_default is None or target_default not in current_default:
                             await conn.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN "{col_name}" SET DEFAULT {target_default}')
                             table_changed = True
                    elif current_default is not None:
                        await conn.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN "{col_name}" DROP DEFAULT')
                        table_changed = True
            if is_enable_drop_column_mismatch:
                desired_cols = {col_cfg["name"] for col_cfg in column_configs}
                for col_name in list(current_cols):
                    if col_name not in desired_cols:
                        await conn.execute(f'ALTER TABLE "{table_name}" DROP COLUMN "{col_name}"')
                        table_changed = True
            for col_cfg in column_configs:
                if col_cfg.get("is_primary") == 1:
                    continue
                col_name = col_cfg["name"]
                col_type = col_cfg["datatype"]
                if col_cfg.get("index"):
                    for index_group in (x.strip() for x in col_cfg["index"].split("|")):
                        if "(" in index_group and index_group.endswith(")"):
                            index_type, cols_str = index_group[:-1].split("(", 1)
                            index_type = index_type.strip().lower()
                            index_cols = [c.strip() for c in cols_str.split(",")]
                            idx_name = clamp_identifier(f"idx_{table_name}_{'_'.join(index_cols)}_{index_type}")
                            catalog["idx"].add(idx_name)
                            if idx_name not in existing_meta:
                                # access method + operator class derived from the explicit token
                                access_method, opclass = ("gin", "gin_trgm_ops") if index_type == "gin_trgm" else (index_type, None)
                                if opclass:
                                    await conn.execute(f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON "{table_name}" USING {access_method}("{index_cols[0]}" {opclass});')
                                else:
                                    cols_quoted = ", ".join([f'"{c}"' for c in index_cols])
                                    await conn.execute(f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON "{table_name}" USING {access_method}({cols_quoted});')
                                table_changed = True
                if is_enabled_col_setting(col_cfg, "in"):
                    chk_name = f"check_{table_name}_{col_name}_in_{get_hash(col_cfg['in'])}"
                    catalog["chk"].add(chk_name)
                    if chk_name not in existing_meta:
                        old_col_name = renamed_cols.get(col_name, col_name)
                        old_chk_name = f"check_{table_name}_{old_col_name}_in_{get_hash(col_cfg['in'])}"
                        if old_chk_name in existing_meta and old_chk_name != chk_name:
                            await conn.execute(f'ALTER TABLE "{table_name}" RENAME CONSTRAINT "{old_chk_name}" TO "{chk_name}"')
                            existing_meta.remove(old_chk_name)
                            existing_meta.add(chk_name)
                        else:
                            await conn.execute(f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{chk_name}" CHECK ("{col_name}" IN {col_cfg["in"]});')
                            table_changed = True
                if is_enabled_col_setting(col_cfg, "regex"):
                    regex_name = f"check_{table_name}_{col_name}_regex_{get_hash(col_cfg['regex'])}"
                    catalog["chk"].add(regex_name)
                    if regex_name not in existing_meta:
                        old_col_name = renamed_cols.get(col_name, col_name)
                        old_regex_name = f"check_{table_name}_{old_col_name}_regex_{get_hash(col_cfg['regex'])}"
                        if old_regex_name in existing_meta and old_regex_name != regex_name:
                            await conn.execute(f'ALTER TABLE "{table_name}" RENAME CONSTRAINT "{old_regex_name}" TO "{regex_name}"')
                            existing_meta.remove(old_regex_name)
                            existing_meta.add(regex_name)
                        else:
                            await conn.execute(f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{regex_name}" CHECK ("{col_name}" ~ \'{col_cfg["regex"]}\');')
                            table_changed = True
                if is_enabled_col_setting(col_cfg, "check"):
                    vld_name = f"check_{table_name}_{col_name}_vld_{get_hash(col_cfg['check'])}"
                    catalog["chk"].add(vld_name)
                    if vld_name not in existing_meta:
                        old_col_name = renamed_cols.get(col_name, col_name)
                        old_vld_name = f"check_{table_name}_{old_col_name}_vld_{get_hash(col_cfg['check'])}"
                        if old_vld_name in existing_meta and old_vld_name != vld_name:
                            await conn.execute(f'ALTER TABLE "{table_name}" RENAME CONSTRAINT "{old_vld_name}" TO "{vld_name}"')
                            existing_meta.remove(old_vld_name)
                            existing_meta.add(vld_name)
                        else:
                            await conn.execute(f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{vld_name}" CHECK ({col_cfg["check"]});')
                            table_changed = True
                if col_cfg.get("unique"):
                    for group in col_cfg["unique"].split("|"):
                        unique_cols = [x.strip() for x in group.split(",")]
                        uni_name = f"""unique_{table_name}_{"_".join(unique_cols)}"""
                        catalog["uni"].add(uni_name)
                        if uni_name not in existing_meta:
                            old_unique_cols = [renamed_cols.get(c, c) for c in unique_cols]
                            old_uni_name = f"""unique_{table_name}_{"_".join(old_unique_cols)}"""
                            if old_uni_name in existing_meta and old_uni_name != uni_name:
                                await conn.execute(f'ALTER TABLE "{table_name}" RENAME CONSTRAINT "{old_uni_name}" TO "{uni_name}"')
                                existing_meta.remove(old_uni_name)
                                existing_meta.add(uni_name)
                            else:
                                cols_quoted = ",".join([f'"{x}"' for x in unique_cols])
                                await conn.execute(f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{uni_name}" UNIQUE ({cols_quoted});')
                                table_changed = True
            if table_changed:
                await conn.execute(f'ANALYZE "{table_name}";')
        db_schema_rows = await conn.fetch("SELECT c.table_name, c.column_name FROM information_schema.columns c JOIN information_schema.tables t ON c.table_name = t.table_name AND c.table_schema = t.table_schema WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE'")
        db_tables = {}
        for row in db_schema_rows:
            db_tables.setdefault(row[0], []).append(row[1])
        users_cols = db_tables.get("users", [])
        if users_cols:
            if is_enable_root_user_delete_disable:
                catalog["tg"].add("trigger_protect_root_users")
                await conn.execute("CREATE OR REPLACE FUNCTION func_protect_root_users() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF TG_OP = 'DELETE' THEN IF OLD.id = 1 THEN RAISE EXCEPTION 'DELETE not allowed for root user (id=1)'; END IF; RETURN OLD; END IF; RETURN NULL; END; $$; DROP TRIGGER IF EXISTS trigger_protect_root_users ON users; CREATE TRIGGER trigger_protect_root_users BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_protect_root_users();")
            if is_enable_root_user_create and all(c in users_cols for c in ("username", "password", "role", "deleted_at", "deactivated_at")):
                if not root_user_password_hash:
                    root_user_password_hash = "$argon2id$v=19$m=65536,t=3,p=4$XXabrpBeXx2PeIcUC7cxWA$CqF+8i+q+k62/6MkQMXFcyMGoTeWmDMvwf8u7WvnrG8"
                await conn.execute("INSERT INTO users (username, password, role) VALUES ('admin', $1, 1) ON CONFLICT (username, role) DO UPDATE SET username = 'admin', password = COALESCE(users.password, EXCLUDED.password), role = 1, deleted_at = NULL, deactivated_at = NULL;", root_user_password_hash)
                await conn.execute("UPDATE users SET username = 'admin', password = COALESCE(users.password, $1), role = 1, deleted_at = NULL, deactivated_at = NULL WHERE id = 1;", root_user_password_hash)
            if is_enable_log_users_password and "password" in users_cols and "log_users_password" in db_tables:
                catalog["tg"].add("trigger_password_log_users")
                await conn.execute("CREATE OR REPLACE FUNCTION func_password_log_users() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.password IS DISTINCT FROM NEW.password THEN INSERT INTO log_users_password (user_id, password, created_by_id) VALUES (NEW.id, NEW.password, NEW.updated_by_id); END IF; RETURN NEW; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_password_log_users ON users; CREATE TRIGGER trigger_password_log_users AFTER UPDATE ON users FOR EACH ROW EXECUTE FUNCTION func_password_log_users();")
            if is_enable_log_users_delete and "deleted_at" in users_cols and "log_users_delete" in db_tables:
                catalog["tg"].add("trigger_log_users_delete")
                await conn.execute("CREATE OR REPLACE FUNCTION func_log_users_delete() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF TG_OP = 'UPDATE' THEN IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN INSERT INTO log_users_delete (user_id, type, created_by_id) VALUES (NEW.id, 1, COALESCE(NEW.deleted_by_id, NEW.updated_by_id)); ELSIF OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS NULL THEN INSERT INTO log_users_delete (user_id, type, created_by_id) VALUES (NEW.id, 2, NEW.updated_by_id); END IF; RETURN NEW; ELSIF TG_OP = 'DELETE' THEN INSERT INTO log_users_delete (user_id, type) VALUES (OLD.id, 3); RETURN OLD; END IF; RETURN NULL; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_log_users_delete ON users; CREATE TRIGGER trigger_log_users_delete AFTER UPDATE OF deleted_at OR DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_log_users_delete();")
            if is_enable_users_role_delete_disable_hard and "role" in users_cols:
                catalog["tg"].add("trigger_delete_disable_role_users")
                await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_role_users() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.role IS NOT NULL THEN RAISE EXCEPTION 'DELETE not allowed for user with role'; END IF; RETURN OLD; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_delete_disable_role_users ON users; CREATE TRIGGER trigger_delete_disable_role_users BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_delete_disable_role_users();")
            if is_enable_users_role_delete_disable_soft and all(c in users_cols for c in ("role", "deleted_at")):
                catalog["tg"].add("trigger_delete_disable_role_users_soft")
                await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_role_users_soft() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.role IS NOT NULL AND OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN RAISE EXCEPTION 'soft DELETE not allowed for user with role'; END IF; RETURN NEW; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_delete_disable_role_users_soft ON users; CREATE TRIGGER trigger_delete_disable_role_users_soft BEFORE UPDATE OF deleted_at ON users FOR EACH ROW EXECUTE FUNCTION func_delete_disable_role_users_soft();")
        await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_is_protected() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.is_protected IS TRUE THEN RAISE EXCEPTION 'DELETE not allowed for protected row in %', TG_TABLE_NAME; END IF; RETURN OLD; END; $$;")
        await conn.execute("CREATE OR REPLACE FUNCTION func_set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at=NOW(); RETURN NEW; END; $$;")
        await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_bulk() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE n BIGINT := TG_ARGV[0]; BEGIN IF (SELECT COUNT(*) FROM deleted_rows) > n THEN RAISE EXCEPTION 'cant delete more than % rows',n; END IF; RETURN OLD; END; $$;")
        await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_table() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'operation not allowed on %', TG_TABLE_NAME; END; $$;")
        drop_tags = []
        if not is_enable_drop_schema: drop_tags.append("'DROP SCHEMA'")
        if not is_enable_drop_table: drop_tags.append("'DROP TABLE'")
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
            if not is_enable_truncate_table:
                trunc_tg_name = f"trigger_truncate_disable_{table}"
                catalog["tg"].add(trunc_tg_name)
                await conn.execute(f"DROP TRIGGER IF EXISTS {trunc_tg_name} ON {table}; CREATE TRIGGER {trunc_tg_name} BEFORE TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION func_delete_disable_table();")
            if is_enable_is_protected_delete_disable and "is_protected" in cols:
                prot_tg_name = f"trigger_delete_disable_is_protected_{table}"
                catalog["tg"].add(prot_tg_name)
                await conn.execute(f"DROP TRIGGER IF EXISTS {prot_tg_name} ON {table}")
                await conn.execute(f"CREATE TRIGGER {prot_tg_name} BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION func_delete_disable_is_protected();")
            if is_enable_updated_at_set and "updated_at" in cols:
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
        managed_tables = list(config_db["table"].keys())
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
        for query in iter_sql_queries(config_db.get("sql", {})):
            await conn.execute(query)
    return "database init done"

async def func_auth_user_login_fetch(*, conn: any, field: str, value: any, role: any) -> dict:
    """Fetch a single login user by a unique-ish field with optional role. Raise on not-found or ambiguity (role omitted but multiple rows)."""
    allowed_fields = ("username", "email", "mobile")
    if field not in allowed_fields: raise Exception(f"invalid auth field: {field}")
    records = await conn.fetch(f'SELECT * FROM users WHERE "{field}"=$2 AND ($1::smallint IS NULL OR role=$1) ORDER BY id DESC LIMIT 2;', role, value)
    if not records: raise Exception(f"{field} not found")
    if role is None and len(records) > 1: raise Exception("role is mandatory")
    return dict(records[0])

async def func_token_encode(*, user: dict, config_token_secret_key: str, config_access_token_expires_sec: int, config_refresh_token_expires_sec: int, config_column_token_encode: list) -> dict:
    """Generate access and refresh JWT tokens for a user object."""
    import jwt, orjson, time
    if user is None: return None
    if config_token_secret_key in (None, ""): raise Exception("token secret key missing")
    token_secret_key = str(config_token_secret_key)
    payload_dict = {k: user.get(k) for k in config_column_token_encode} if config_column_token_encode else dict(user) if isinstance(user, dict) else user
    serialized_payload = orjson.dumps(payload_dict, default=str).decode("utf-8")
    now_ts = int(time.time())
    access_token_expires_at = now_ts + config_access_token_expires_sec
    refresh_token_expires_at = now_ts + config_refresh_token_expires_sec
    access_token = jwt.encode({"exp": access_token_expires_at, "data": serialized_payload, "type": "access"}, token_secret_key)
    refresh_token = jwt.encode({"exp": refresh_token_expires_at, "data": serialized_payload, "type": "refresh"}, token_secret_key)
    return {"access_token": access_token, "refresh_token": refresh_token, "access_token_expires_at": access_token_expires_at, "refresh_token_expires_at": refresh_token_expires_at}

async def func_token_decode(*, headers: dict, config_token_secret_key: str) -> dict:
    """Decode Bearer token if present; return decoded user dict or empty dict."""
    auth_header = headers.get("Authorization")
    token = auth_header.split("Bearer ", 1)[1] if auth_header and auth_header.startswith("Bearer ") else None
    if not token: return {}
    import jwt, orjson
    if config_token_secret_key in (None, ""): raise Exception("token secret key missing")
    decoded_payload = jwt.decode(token, str(config_token_secret_key), algorithms="HS256")
    user = orjson.loads(decoded_payload["data"])
    if isinstance(user, dict): user["_token_type"] = decoded_payload.get("type")
    return user

async def func_middleware_check_auth(*, user_dict: dict, url_path: str, is_token: int = 0, user_check_role: list = None, user_check_deactivated: list = None, user_check_deleted: list = None) -> None:
    """Check whether current API requires token-authenticated user."""
    is_token_required = is_token in (1, "1", True, "true") or bool(user_check_role) or bool(user_check_deactivated) or bool(user_check_deleted)
    if is_token_required:
        if not user_dict: raise Exception("authorization token missing")
        token_type = user_dict.get("_token_type") if isinstance(user_dict, dict) else None
        if url_path == "/my/token-refresh":
            if token_type != "refresh": raise Exception("refresh token required")
        elif token_type != "access":
            raise Exception("access token required")
    return None

async def func_middleware_check_user_deactivated(*, user_dict: dict, user_check_deactivated: list, client_postgres: any, client_redis: any, cache_users_deactivated: dict, config_redis_cache_ttl_sec: int) -> None:
    """Check if the user is deactivated using a strictly configured mode from config_api."""
    cfg = user_check_deactivated
    if not cfg or not user_dict: return None
    mode = cfg[0]
    if not mode: return None
    async def fetch_deactivated_status(uid):
        if not client_postgres: raise Exception("postgres client missing")
        async with client_postgres.acquire() as conn:
            rows = await conn.fetch("select id, deactivated_at from users where id=$1", uid)
        if not rows: raise Exception("user not found")
        return rows[0]["deactivated_at"]
    if mode == "redis":
        if not client_redis: raise Exception("redis client missing")
        cache_key = f"""cache:user:active:{user_dict["id"]}"""
        active_status = None
        cached_val = await client_redis.get(cache_key)
        if cached_val is not None:
            active_status = cached_val if cached_val != 'None' else None
        else:
            active_status = await fetch_deactivated_status(user_dict["id"])
            await client_redis.setex(cache_key, config_redis_cache_ttl_sec, str(active_status))
    elif mode == "realtime":
        active_status = await fetch_deactivated_status(user_dict["id"])
    elif mode == "inmemory":
        active_status = cache_users_deactivated.get(user_dict["id"], "absent")
        if active_status == "absent":
            active_status = await fetch_deactivated_status(user_dict["id"])
    elif mode == "token":
        active_status = user_dict.get("deactivated_at", "absent")
    else:
        raise Exception(f"invalid mode: {mode}, allowed: redis, realtime, inmemory, token")
    if active_status == "absent": raise Exception("missing deactivated_at")
    if active_status is not None: raise Exception("user not active")

async def func_middleware_check_user_deleted(*, user_dict: dict, user_check_deleted: list, client_postgres: any, client_redis: any, cache_users_deleted: dict, config_redis_cache_ttl_sec: int) -> None:
    """Check if the user is deleted using a strictly configured mode from config_api."""
    cfg = user_check_deleted
    if not cfg or not user_dict: return None
    mode = cfg[0]
    if not mode: return None
    async def fetch_deleted(uid):
        if not client_postgres: raise Exception("postgres client missing")
        async with client_postgres.acquire() as conn:
            rows = await conn.fetch("select deleted_at from users where id=$1", uid)
        if not rows: raise Exception("user not found")
        return rows[0]["deleted_at"]
    if mode == "redis":
        if not client_redis: raise Exception("redis client missing")
        cache_key = f"""cache:user:deleted_at:{user_dict["id"]}"""
        deleted_status = None
        cached_val = await client_redis.get(cache_key)
        if cached_val is not None:
            deleted_status = cached_val if cached_val != "None" else None
        else:
            deleted_status = await fetch_deleted(user_dict["id"])
            await client_redis.setex(cache_key, config_redis_cache_ttl_sec, str(deleted_status))
    elif mode == "realtime":
        deleted_status = await fetch_deleted(user_dict["id"])
    elif mode == "inmemory":
        deleted_status = cache_users_deleted.get(user_dict["id"], "absent")
        if deleted_status == "absent":
            deleted_status = await fetch_deleted(user_dict["id"])
    elif mode == "token":
        deleted_status = user_dict.get("deleted_at", "absent")
    else:
        raise Exception(f"invalid mode: {mode}, allowed: redis, realtime, inmemory, token")
    if deleted_status == "absent": raise Exception("missing deleted_at")
    if deleted_status is not None: raise Exception("user is deleted")

async def func_middleware_check_role(*, user_dict: dict, user_check_role: list, client_postgres: any, client_redis: any, cache_users_role: dict, config_redis_cache_ttl_sec: int) -> None:
    """Ensure sufficient roles to access endpoints using a strictly configured mode from config_api."""
    cfg = user_check_role
    if not cfg: return None
    if not user_dict: raise Exception("authorization token missing")
    mode = cfg[0]
    roles = {int(role) for role in cfg[1]}
    async def fetch_role(uid):
        if not client_postgres: raise Exception("postgres client missing")
        async with client_postgres.acquire() as conn:
            rows = await conn.fetch("select role from users where id=$1", uid)
        if not rows: raise Exception("user not found")
        return rows[0]["role"]
    if mode == "redis":
        if not client_redis: raise Exception("redis client missing")
        cache_key = f"""cache:user:role:{user_dict["id"]}"""
        user_role = None
        cached_val = await client_redis.get(cache_key)
        if cached_val is not None:
            user_role = int(cached_val)
        else:
            user_role = await fetch_role(user_dict["id"])
            await client_redis.setex(cache_key, config_redis_cache_ttl_sec, str(user_role if user_role is not None else ""))
    elif mode == "realtime":
        user_role = await fetch_role(user_dict["id"])
    elif mode == "inmemory":
        user_role = cache_users_role.get(user_dict["id"])
        if user_role is None:
            user_role = await fetch_role(user_dict["id"])
    elif mode == "token":
        user_role = user_dict.get("role", "absent")
    else:
        raise Exception(f"invalid mode: {mode}, allowed: redis, realtime, inmemory, token")
    if user_role == "absent": raise Exception("user role missing")
    if user_role is None or user_role == "": raise Exception("user role is null")
    if user_role == "role": raise Exception("user role is invalid")
    if not isinstance(user_role, int):
        try:
            user_role = int(user_role)
        except Exception:
            raise Exception("invalid user role type")
    if user_role not in roles: raise Exception("access denied")

async def func_middleware_check_ratelimiter(*, client_redis: any, api_ratelimiting_times_sec: list, url_path: str, identifier: str, cache_ratelimiter: dict) -> None:
    """Check and enforce API rate limits using either Redis or in-memory storage."""
    import time
    rl_config = api_ratelimiting_times_sec
    if not rl_config: return None
    mode, limit, window = rl_config
    limit, window = int(limit), int(window)
    if limit <= 0 or window <= 0: return None
    cache_key = f"ratelimiter:{url_path}:{identifier}"
    if mode == "redis":
        if not client_redis: raise Exception("redis client missing")
        current_count = await client_redis.get(cache_key)
        if current_count and int(current_count) + 1 > limit:
            raise Exception("ratelimiter exceeded")
        pipeline = client_redis.pipeline()
        pipeline.incr(cache_key)
        if not current_count:
            pipeline.expire(cache_key, window)
        await pipeline.execute()
    elif mode == "inmemory":
        now = time.time()
        item = cache_ratelimiter.get(cache_key)
        if item and item["expire_at"] > now:
            if item["count"] + 1 > limit:
                raise Exception("ratelimiter exceeded")
            item["count"] += 1
        else:
            cache_ratelimiter[cache_key] = {"count": 1, "expire_at": now + window}
    else:
        raise Exception(f"invalid ratelimiter mode: {mode}, allowed: redis, inmemory")
    return None

async def func_middleware_api_cache(*, mode: str, path: str, query_params: dict, api_cache_sec: list, client_redis: any = None, user_id: int = 0, cache_api_response: dict = None, response: any = None) -> any:
    """Get or set middleware API cache for a request."""
    from fastapi import Response
    import gzip, base64, time
    if mode not in ("get", "set"): raise Exception(f"invalid cache operation: {mode}, allowed: get, set")
    cfg = api_cache_sec
    cache_mode = cfg[0] if cfg else None
    ttl = int(cfg[1]) if cfg else 0
    is_user_cache = cfg[2] if cfg else 0
    is_user_cache = str(is_user_cache) == "1" or is_user_cache is True
    is_enabled = query_params.get("is_disable_cache") != "1" and bool(cfg) and bool(cache_mode) and ttl > 0
    if mode == "set" and not is_enabled: return response
    if mode == "get" and not is_enabled: return None
    if cache_api_response is None: cache_api_response = {}
    uid = user_id if is_user_cache else 0
    key = f"cache:{path}?{'&'.join(f'{k}={v}' for k, v in sorted(query_params.items()))}:{uid}"
    if mode == "get":
        data = await client_redis.get(key) if cache_mode == "redis" else (item["data"] if (item := cache_api_response.get(key)) and item["expire_at"] > time.time() else None)
        return Response(content=gzip.decompress(base64.b64decode(data)).decode(), status_code=200, media_type="application/json", headers={"x-cache": "hit"}) if data else None
    body = getattr(response, "body", None) or b"".join([chunk async for chunk in response.body_iterator])
    comp = base64.b64encode(gzip.compress(body)).decode()
    if cache_mode == "redis": await client_redis.setex(key, ttl, comp)
    else: cache_api_response[key] = {"data": comp, "expire_at": time.time() + ttl}
    response = Response(content=body, status_code=response.status_code, media_type=response.media_type, headers=dict(response.headers))
    response.is_cache_set = True
    return response

async def func_middleware_api_background(*, scope: dict, body_bytes: bytes, api_function: callable) -> any:
    """Delegate the request execution to a background task and return a standard acknowledgment."""
    import asyncio
    from fastapi import Request, responses
    async def receive(): return {"type": "http.request", "body": body_bytes}
    async def task():
        try:
            await api_function(Request(scope=scope, receive=receive))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"❌ background api error: {e}")
    task_obj = asyncio.create_task(task())
    app = scope.get("app")
    task_set = getattr(getattr(app, "state", None), "runtime_background_tasks", None) if app else None
    if task_set is not None:
        task_set.add(task_obj)
        task_obj.add_done_callback(task_set.discard)
    resp = responses.JSONResponse(status_code=200, content={"status": 1, "message": "added in background"})
    return resp

async def func_middleware_api_response_error(*, exception: Exception, is_traceback: int, sentry_dsn: str) -> tuple:
    """Central API error handler: formats database, client, and system exceptions into a standard JSON response."""
    import traceback, asyncpg, re, botocore.exceptions, redis.exceptions, httpx, jwt.exceptions
    from fastapi import responses
    if isinstance(exception, asyncpg.exceptions.UniqueViolationError):
        column = re.findall(r"\((.*?)\)=", exception.detail or "")
        error_msg = (column[0].replace("_", " ") + " already exists") if column else "duplicate value"
    elif isinstance(exception, asyncpg.exceptions.CheckViolationError):
        constraint = exception.constraint_name or ""
        error_msg = re.sub(r"^constraint_|_regex$", "", constraint).replace("_", " ") + " invalid"
    elif isinstance(exception, asyncpg.exceptions.ForeignKeyViolationError):
        column = re.findall(r"\((.*?)\)=", exception.detail or "")
        error_msg = (column[0].replace("_", " ") + " invalid reference") if column else "invalid reference"
    elif isinstance(exception, asyncpg.exceptions.NotNullViolationError):
        column = re.findall(r"\"(.*?)\"", exception.message or "")
        error_msg = (column[0].replace("_", " ") + " required") if column else "missing required field"
    elif isinstance(exception, asyncpg.exceptions.InvalidTextRepresentationError):
        error_msg = "invalid database input text format"
    elif isinstance(exception, asyncpg.exceptions.NumericValueOutOfRangeError):
        error_msg = "invalid database input numeric range"
    elif isinstance(exception, asyncpg.exceptions.StringDataRightTruncationError):
        error_msg = "invalid database input string truncation"
    elif isinstance(exception, asyncpg.exceptions.DeadlockDetectedError):
        error_msg = "database conflict deadlock detected"
    elif isinstance(exception, asyncpg.exceptions.SerializationError):
        error_msg = "database conflict serialization error"
    elif isinstance(exception, botocore.exceptions.ClientError):
        error_msg = f"""cloud service error: {exception.response.get("Error", {}).get("Code", "Unknown")}"""
    elif isinstance(exception, redis.exceptions.RedisError):
        error_msg = "cache service error"
    elif isinstance(exception, jwt.exceptions.PyJWTError):
        error_msg = "authentication token invalid"
    elif isinstance(exception, httpx.HTTPStatusError):
        error_msg = f"external api error: {exception.response.status_code}"
    else:
        error_msg = str(exception)
    if is_traceback:
        traceback.print_exception(type(exception), exception, exception.__traceback__)
    if sentry_dsn:
        import sentry_sdk
        sentry_sdk.capture_exception(exception)
    return error_msg, responses.JSONResponse(status_code=400, content={"status": 0, "message": error_msg})
    
async def func_request_param_read(*, request: any, mode: str, strict: int, param_specs: list) -> dict:
    """Extract, validate, and type-cast request parameters from query, form, body or headers."""
    params_dict = {}
    header_params = {k.lower(): v for k, v in request.headers.items()}
    if mode == "query":
        params_dict = dict(request.query_params)
    elif mode == "form":
        form_data = await request.form()
        params_dict = {key: val for key, val in form_data.items() if isinstance(val, str)}
        for key in form_data.keys():
            files = [x for x in form_data.getlist(key) if not isinstance(x, str)]
            if files:
                params_dict[key] = files
    elif mode == "body":
        try:
            json_payload = await request.json()
        except Exception:
            json_payload = None
        params_dict = json_payload if isinstance(json_payload, dict) else {"body": json_payload}
    elif mode == "header":
        params_dict = header_params
    else:
        raise Exception(f"invalid mode: {mode}")
    if param_specs is None: return params_dict
    import orjson
    def smart_dict(v):
        if v is None: return {}
        if isinstance(v, dict): return v
        if isinstance(v, str):
            v = v.strip()
            if not v: return {}
            if v.startswith("{"): return orjson.loads(v)
        return {}
    def smart_list(v):
        if v is None: return []
        if isinstance(v, list): return v
        if isinstance(v, str):
            v = v.strip()
            if not v: return []
            if v.startswith("[") or v.startswith("{"):
                parsed = orjson.loads(v)
                return parsed if isinstance(parsed, list) else [parsed]
            return [x.strip() for x in v.split(",") if x.strip()]
        return [v]
    TYPE_MAP = {
        "int": int, "bigint": int, "smallint": int, "integer": int, "int4": int, "int8": int,
        "float": float, "number": float, "numeric": float,
        "str": str, "any": lambda v: v, 
        "bool": lambda v: 1 if str(v).strip().lower() in ("1", "true", "yes", "on", "ok") else 0, 
        "dict": smart_dict, "object": smart_dict,
        "file": lambda v: [x for x in (v if isinstance(v, list) else [v] if v is not None else []) if hasattr(x, "file")],
        "list": smart_list
    }
    output_dict = params_dict.copy() if not strict else {}
    for param_spec in param_specs:
        if not isinstance(param_spec, dict): raise Exception(f"invalid parameter specification: expected dict, got {type(param_spec)}")
        if "name" not in param_spec or "type" not in param_spec: raise Exception("parameter specification requires 'name' and 'type'")
        key = param_spec["name"]
        dtype = param_spec["type"]
        is_mandatory = int(param_spec.get("required", False))
        allowed_values = param_spec.get("allowed")
        default_value = param_spec.get("default")
        if dtype not in TYPE_MAP and not dtype.startswith("list:"): raise Exception(f"parameter '{key}' has invalid dtype '{dtype}'")
        if is_mandatory == 1 and default_value is not None: raise Exception(f"parameter '{key}' is mandatory, default_value must be None")
        if default_value is not None and allowed_values is not None and default_value not in allowed_values:
            raise Exception(f"parameter '{key}' default '{default_value}' violating allowed_values: {allowed_values}")
        if allowed_values is not None and not isinstance(allowed_values, (list, tuple)): raise Exception(f"parameter '{key}' allowed_values must be a list or tuple")
        val = params_dict.get(key)
        if val is None:
            val = header_params.get(key.lower())
        if val is None:
            val = default_value
        if isinstance(val, str) and val.lower() in ("null", "undefined"):
            val = default_value
        if dtype == "file" and isinstance(val, str):
            hint = f" received '{val}'" if val else ""
            raise Exception(f"parameter '{key}' expected file upload but received text field{hint}; use curl -F '{key}=@/path/to/file'")
        if is_mandatory == 1:
            if val is None:
                raise Exception(f"parameter '{key}' missing")
            if isinstance(val, str) and not val.strip():
                raise Exception(f"parameter '{key}' cannot be empty")
        if val is not None:
            try:
                if dtype.startswith("list:") and ":" in dtype:
                    inner_type = dtype.split(":")[1]
                    val_list = TYPE_MAP["list"](val)
                    val = [TYPE_MAP[inner_type](x) for x in val_list]
                else:
                    val = TYPE_MAP[dtype](val)
            except Exception:
                raise Exception(f"parameter '{key}' invalid type {dtype}")
        if is_mandatory == 1:
            if dtype == "file" and (not isinstance(val, list) or len(val) == 0):
                raise Exception(f"parameter '{key}' missing or invalid file upload")
            if dtype == "list" and (not isinstance(val, list) or len(val) == 0):
                 raise Exception(f"parameter '{key}' missing or empty list")
        if val is not None and allowed_values is not None and val not in allowed_values: raise Exception(f"parameter '{key}' value not allowed, allowed: {allowed_values}")
        output_dict[key] = val
    return output_dict


def func_openapi_spec_generate(*, app_routes: list, app_state: any) -> dict:
    """Generate a standard OpenAPI 3.0.0 specification from FastAPI routes using source inspection."""
    import inspect, re, ast
    config_api = getattr(app_state, "config_api", {}) or {}
    TYPE_MAP = {
        "int": "integer", "bigint": "integer", "smallint": "integer", "integer": "integer", "int4": "integer", "int8": "integer",
        "float": "number", "number": "number", "numeric": "number",
        "bool": "boolean", "dict": "object", "object": "object", "file": "string", "list": "array"
    }
    def eval_node(n):
        if hasattr(ast, "Constant") and isinstance(n, ast.Constant): return n.value
        if hasattr(ast, "Str") and isinstance(n, ast.Str): return n.s
        if hasattr(ast, "Num") and isinstance(n, ast.Num): return n.n
        if hasattr(ast, "NameConstant") and isinstance(n, ast.NameConstant): return n.value
        if isinstance(n, (ast.List, ast.Tuple)): return [eval_node(e) for e in n.elts]
        if isinstance(n, ast.Dict): return {eval_node(k): eval_node(v) for k, v in zip(n.keys, n.values)}
        if isinstance(n, ast.Attribute) and hasattr(n.value, "id") and n.value.id == "app_state" and app_state: return getattr(app_state, n.attr, None)
        if isinstance(n, ast.IfExp): return eval_node(n.body) if eval_node(n.test) else eval_node(n.orelse)
        if isinstance(n, ast.Compare):
            left = eval_node(n.left)
            for op, r_node in zip(n.ops, n.comparators):
                right = eval_node(r_node)
                if isinstance(op, ast.NotEq) and not (left != right): return False
                if isinstance(op, ast.Eq) and not (left == right): return False
                if isinstance(op, ast.In) and not (left in right): return False
                if isinstance(op, ast.NotIn) and not (left not in right): return False
            return True
        if isinstance(n, ast.ListComp) and len(n.generators) == 1:
            gen = n.generators[0]
            items = eval_node(gen.iter)
            if items is None or not isinstance(items, list): return None
            if not gen.ifs: return items
            if len(gen.ifs) == 1 and isinstance(gen.ifs[0], ast.Compare):
                comp = gen.ifs[0]
                if isinstance(comp.left, ast.Name) and comp.left.id == gen.target.id:
                    if len(comp.ops) == 1 and len(comp.comparators) == 1:
                        other = eval_node(comp.comparators[0])
                        if other is not None and isinstance(other, (list, tuple, set)):
                            if isinstance(comp.ops[0], ast.NotIn): return [it for it in items if it not in other]
                            if isinstance(comp.ops[0], ast.In): return [it for it in items if it in other]
            return items
        if isinstance(n, ast.BoolOp):
            vals = [eval_node(v) for v in n.values]
            return all(vals) if isinstance(n.op, ast.And) else any(vals)
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            l, r = eval_node(n.left), eval_node(n.right)
            if l is not None and r is not None: return l + r
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "list" and len(n.args) > 0:
            v = eval_node(n.args[0])
            if v is not None: return list(v)
        return None
    def ast_to_schema(n):
        if isinstance(n, ast.Dict):
            return {"type": "object", "properties": {eval_node(k): ast_to_schema(v) for k, v in zip(n.keys, n.values) if eval_node(k)}}
        if isinstance(n, (ast.List, ast.Tuple)):
            return {"type": "array", "items": ast_to_schema(n.elts[0]) if n.elts else {"type": "string"}}
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
            s1, s2 = ast_to_schema(n.left), ast_to_schema(n.right)
            return {"type": "object", "properties": {**(s1.get("properties", {})), **(s2.get("properties", {}))}}
        v = eval_node(n)
        if isinstance(v, (int, float, bool)): return {"type": "integer" if isinstance(v, int) else "number" if isinstance(v, float) else "boolean", "default": v}
        if isinstance(v, list): return {"type": "array", "items": {"type": "string"}}
        if isinstance(v, dict): return {"type": "object", "properties": {k: {"type": "string", "default": str(val)} for k, val in v.items()}}
        return {"type": "string", "default": str(v) if v is not None else None}
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "API Documentation", "version": "1.0.0"},
        "paths": {},
        "components": {"securitySchemes": {"BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}}
    }
    for route in app_routes:
        if not hasattr(route, "path") or not hasattr(route, "endpoint"): continue
        path = route.path
        if path not in spec["paths"]: spec["paths"][path] = {}
        methods = list(getattr(route, "methods", [])) or (["WS"] if "WebSocket" in type(route).__name__ else [])
        for method in methods:
            m_lower = method.lower()
            tag = path.split("/")[1] if len(path.split("/")) > 1 and path.split("/")[1] else "system"
            op = {"tags": [tag], "parameters": [], "responses": {"200": {"description": "Successful Response"}}}
            api_cfg = config_api.get(path, {})
            is_token_required = api_cfg.get("is_token") in (1, "1", True, "true") or "user_check_role" in api_cfg
            op["x-auth-required"] = is_token_required
            op["x-roles-allowed"] = api_cfg.get("user_check_role", None)
            op["x-check-deactivated"] = "user_check_deactivated" in api_cfg
            op["x-check-deleted"] = "user_check_deleted" in api_cfg
            op["x-cache"] = api_cfg.get("api_cache_sec", None)
            op["x-rate-limit"] = api_cfg.get("api_ratelimiting_times_sec", None)
            if is_token_required:
                op["security"] = [{"BearerAuth": []}]
                op["parameters"].append({"name": "Authorization", "in": "header", "required": True, "schema": {"type": "string", "default": "Bearer {token}"}})
            for p in re.findall(r"\{(\w+)\}", path):
                op["parameters"].append({"name": p, "in": "path", "required": True, "schema": {"type": "string"}})
            try:
                sig = inspect.signature(route.endpoint)
                for name, par in sig.parameters.items():
                    p_type = par.annotation.__name__ if hasattr(par.annotation, "__name__") else str(par.annotation)
                    if name in ["request", "websocket", "req"] or any(x in p_type for x in ["Request", "Response", "WebSocket", "BackgroundTasks"]): continue
                    if any(x["name"] == name for x in op["parameters"]): continue
                    op["parameters"].append({"name": name, "in": "query", "required": par.default == inspect.Parameter.empty, "schema": {"type": "integer" if p_type == "int" else "string", "default": None if par.default == inspect.Parameter.empty else par.default}})
                source = inspect.getsource(route.endpoint)
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Return):
                        try: op["responses"]["200"]["content"] = {"application/json": {"schema": ast_to_schema(node.value)}}
                        except: pass
                    if not isinstance(node, ast.Call): continue
                    func_id = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                    if func_id != "func_request_param_read": continue
                    is_regex_enabled = any(isinstance(n, ast.Call) and (getattr(n.func, "id", None) == "func_regex_check" or getattr(n.func, "attr", None) == "func_regex_check") for n in ast.walk(tree))
                    try:
                        p_loc, p_list = None, None
                        for kw in node.keywords:
                            if kw.arg == "mode": p_loc = eval_node(kw.value)
                            elif kw.arg == "param_specs": p_list = eval_node(kw.value)
                        if p_loc is None and len(node.args) > 1: p_loc = eval_node(node.args[1])
                        if p_list is None and len(node.args) > 2: p_list = eval_node(node.args[2])
                        if p_list is not None and p_loc in ["header", "query"]:
                            for p in p_list:
                                if not isinstance(p, dict) or "name" not in p: continue
                                p_name = p["name"]
                                dt = p.get("type", "str")
                                op["parameters"] = [x for x in op["parameters"] if x["name"] != p_name]
                                tp = TYPE_MAP.get(dt.split(":")[0], "string")
                                itms = {"type": TYPE_MAP.get(dt.split(":")[1], "string")} if ":" in dt else None
                                reg_info = getattr(app_state, "config_regex", {}).get(p_name) if is_regex_enabled else None
                                op["parameters"].append({
                                    "name": p_name, "in": p_loc, "required": bool(p.get("required", False)),
                                    "description": reg_info[1] if reg_info and len(reg_info) > 1 else None,
                                    "schema": {"type": tp, "format": "binary" if dt == "file" else None, **({"items": itms} if itms else {}), "enum": p.get("allowed") if isinstance(p.get("allowed"), (list, tuple)) else None, "default": p.get("default"), "pattern": reg_info[0] if reg_info and len(reg_info) > 0 else None}
                                })
                        elif p_list is not None and p_loc in ["body", "form"]:
                            media_type = "application/json" if p_loc == "body" else "multipart/form-data"
                            if "requestBody" not in op: op["requestBody"] = {"content": {media_type: {"schema": {"type": "object", "properties": {}, "required": []}}}}
                            props, reqs = op["requestBody"]["content"][media_type]["schema"]["properties"], op["requestBody"]["content"][media_type]["schema"]["required"]
                            for p in p_list:
                                if not isinstance(p, dict) or "name" not in p: continue
                                p_name = p["name"]
                                reg_info = getattr(app_state, "config_regex", {}).get(p_name) if is_regex_enabled else None
                                dt = p.get("type", "str")
                                props[p_name] = {"type": TYPE_MAP.get(dt.split(":")[0], "string"), "format": "binary" if dt == "file" else None, **({"items": {"type": TYPE_MAP.get(dt.split(":")[1], "string")}} if ":" in dt else {}), "enum": p.get("allowed") if isinstance(p.get("allowed"), (list, tuple)) else None, "default": p.get("default"), "pattern": reg_info[0] if reg_info and len(reg_info) > 0 else None, "description": reg_info[1] if reg_info and len(reg_info) > 1 else None}
                                if bool(p.get("required", False)): reqs.append(p_name)
                    except: pass
            except: pass
            spec["paths"][path][m_lower] = op
    return spec

def func_app_router_add(*, app: any, router_dir: any, router_order: dict) -> None:
    """Load router modules from a directory in a configured order and include their routers."""
    import importlib.util, pathlib
    router_dir = pathlib.Path(router_dir)
    router_paths = sorted(router_dir.glob("*.py"), key=lambda path: (router_order.get(path.stem, 100), path.stem))
    for router_path in router_paths:
        if router_path.name.startswith(("_", ".")): continue
        spec = importlib.util.spec_from_file_location(f"router.{router_path.stem}", router_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "router"): app.include_router(module.router)
    return None

async def func_regex_check(*, config_regex: dict, obj_list: list) -> None:
    """Validate fields in a list of objects against regex patterns defined in config."""
    import re
    if not config_regex: return None
    for obj in obj_list:
        for key, regex_info in config_regex.items():
            val = obj.get(key)
            if val is not None:
                pattern = regex_info[0]
                error_msg = regex_info[1]
                if not re.match(pattern, str(val)):
                    raise Exception(error_msg)
    return None

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

async def func_blob_url_delete(*, app_state: any, service: str, urls: list, user_id: int = None) -> list:
    """Deletes S3 or Azure blobs by their URLs, optionally enforcing user ownership."""
    import urllib.parse
    import asyncio
    if (service == "s3" and not app_state.client_s3) or (service == "azure" and not app_state.client_azure_blob):
        raise Exception("blob client not initialized")
    tasks = []
    deleted_urls = []
    if service == "s3":
        s3_batches = {}
        for url in urls:
            if not url: continue
            parsed = urllib.parse.urlparse(url)
            host_parts = parsed.netloc.split(".")
            if host_parts[0] != "s3":
                bucket = host_parts[0]
                key = parsed.path.lstrip("/")
            else:
                parts = parsed.path.lstrip("/").split("/", 1)
                if len(parts) != 2: continue
                bucket, key = parts[0], parts[1]
            decoded_key = urllib.parse.unquote(key)
            if user_id is not None and not decoded_key.startswith(f"user_{user_id}/"): continue
            s3_batches.setdefault(bucket, []).append({"Key": decoded_key})
            deleted_urls.append(url)
        for bucket, keys in s3_batches.items():
            for i in range(0, len(keys), 1000):
                tasks.append(app_state.client_s3.delete_objects(Bucket=bucket, Delete={"Objects": keys[i:i+1000], "Quiet": True}))
    elif service == "azure":
        for url in urls:
            if not url: continue
            parsed = urllib.parse.urlparse(url)
            parts = parsed.path.lstrip("/").split("/", 1)
            if len(parts) != 2: continue
            container, key = parts[0], parts[1]
            decoded_key = urllib.parse.unquote(key)
            if user_id is not None and not decoded_key.startswith(f"user_{user_id}/"): continue
            tasks.append(app_state.client_azure_blob.get_blob_client(container=container, blob=decoded_key).delete_blob())
            deleted_urls.append(url)
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                if type(res).__name__ != "ResourceNotFoundError": raise res
        return deleted_urls

async def func_postgres_query_generator_ai(*, app_state: any, db: str, ai: str, question: str) -> dict:
    """Generates and validates safe PostgreSQL SELECT queries using LLM (Gemini/OpenAI) based on the database schema."""
    import re
    import json
    import asyncio
    from google.genai import types

    if ai == "gemini" and not app_state.client_gemini: raise Exception("Gemini client not initialized")
    if ai == "openai" and not app_state.client_openai: raise Exception("OpenAI client not initialized")
    client_postgres = app_state.client_postgres if db == "main" else app_state.client_postgres_external
    cache_key = "cache_postgres_schema_ai" if db == "main" else "cache_postgres_schema_external_ai"
    if not client_postgres: raise Exception(f"{db} postgres client not initialized")
    question = str(question or "").strip()
    default_limit = 10
    max_limit = app_state.config_query_runner_read_limit

    def func_postgres_query_ai_schema_prompt(cache_postgres_schema_ai: dict) -> list:
        output = []
        for table_key, table in sorted((cache_postgres_schema_ai or {}).items()):
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

    def func_postgres_query_ai_resolve_table_key(*, value: str, cache_postgres_schema_ai: dict) -> str:
        value = func_postgres_query_ai_clean_identifier(value)
        if not value: return ""
        value = re.sub(r"\s*\.\s*", ".", value)
        lookup = {key.lower(): key for key in (cache_postgres_schema_ai or {}).keys()}
        lookup.update({str(table.get("table_name") or key.split(".")[-1]).lower(): key for key, table in (cache_postgres_schema_ai or {}).items()})
        return lookup.get(value.lower(), "")

    def func_postgres_query_ai_resolve_column_name(*, table_key: str, value: str, cache_postgres_schema_ai: dict) -> str:
        value = func_postgres_query_ai_clean_identifier(value)
        if not table_key or not value: return ""
        columns = (cache_postgres_schema_ai.get(table_key, {}).get("columns") or {})
        lookup = {column.lower(): column for column in columns.keys()}
        return lookup.get(value.lower(), "")

    def func_postgres_query_ai_validate_sql(*, sql: str, default_limit: int, max_limit: int, cache_postgres_schema_ai: dict) -> str:
        sql = str(sql or "").strip().rstrip(";").strip()
        if not sql: raise Exception("AI did not generate SQL.")
        if ";" in sql: raise Exception("AI generated multiple SQL statements.")
        if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("AI generated non-read SQL.")
        known_tables = set((cache_postgres_schema_ai or {}).keys())
        table_matches = re.findall(r'\b(?:from|join)\s+((?:"[^"]+"|\w+)(?:\s*\.\s*(?:"[^"]+"|\w+))?)(?:\s+(?:as\s+)?("[^"]+"|\w+))?', sql, flags=re.IGNORECASE)
        alias_to_table = {}
        for raw_table, raw_alias in table_matches:
            parts = [part.strip().strip('"') for part in raw_table.split(".")]
            table_key = ".".join(parts) if len(parts) > 1 else f"public.{parts[0]}"
            table_key = func_postgres_query_ai_resolve_table_key(value=table_key, cache_postgres_schema_ai=cache_postgres_schema_ai) or table_key
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
                column_names = [(table_key, func_postgres_query_ai_resolve_column_name(table_key=table_key, value=column, cache_postgres_schema_ai=cache_postgres_schema_ai)) for table_key in candidate_tables]
                column_matches = [cache_postgres_schema_ai[table_key]["columns"][column_name] for table_key, column_name in column_names if column_name]
                if not column_matches: raise Exception(f"AI generated filter on unknown column: {column}")
                if column_matches and not any(col.get("is_indexed") for col in column_matches): raise Exception(f"AI generated filter on non-indexed column: {column}")
        limit_match = re.search(r'\blimit\s+(\d+)\s*$', sql, flags=re.IGNORECASE)
        if limit_match:
            limit = max(1, min(int(limit_match.group(1)), max_limit))
            sql = re.sub(r'\blimit\s+\d+\s*$', f"LIMIT {limit}", sql, flags=re.IGNORECASE)
        else:
            sql = f"{sql}\nLIMIT {default_limit}"
        return f"{sql.rstrip(';')};"

    cache_postgres_schema_ai = getattr(app_state, cache_key, {}) or {}
    if not cache_postgres_schema_ai:
        cache_postgres_schema_ai = await app_state.func_postgres_schema_read_ai(client_postgres=client_postgres)
        setattr(app_state, cache_key, cache_postgres_schema_ai)
    prompt_schema = func_postgres_query_ai_schema_prompt(cache_postgres_schema_ai)
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "sql": {"type": "STRING", "nullable": True},
            "message": {"type": "STRING"},
            "warnings": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
    }
    response_json_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "sql": {"type": ["string", "null"]},
            "message": {"type": "string"},
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["sql", "message", "warnings"],
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
    if ai == "gemini":
        response = await asyncio.to_thread(
            app_state.client_gemini.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=response_schema, temperature=0.1),
        )
        data = json.loads(response.text or "{}")
    else:
        response = await asyncio.to_thread(
            app_state.client_openai.responses.create,
            model="gpt-4.1-mini",
            input=prompt,
            text={"format": {"type": "json_schema", "name": "postgres_query_generator", "schema": response_json_schema, "strict": True}},
            temperature=0.1,
        )
        data = json.loads(response.output_text or "{}")
    if not data.get("sql"):
        return {"sql": None, "message": func_postgres_query_ai_blocked_message(data.get("message")), "warnings": data.get("warnings") or []}
    sql = func_postgres_query_ai_validate_sql(sql=data.get("sql"), default_limit=default_limit, max_limit=max_limit, cache_postgres_schema_ai=cache_postgres_schema_ai)
    return {"sql": sql, "message": "SQL generated in the editor. Review before Run or Export.", "warnings": data.get("warnings") or []}

async def func_jira_worklog_export(*, url: str, email: str, api_token: str, start_date: str, end_date: str) -> str:
    """Exports Jira worklogs within a date range to a CSV file and returns the file path."""
    import os
    import uuid
    import asyncio
    import pandas as pd
    from jira import JIRA

    os.makedirs("tmp", exist_ok=True)
    output_path = f"tmp/{uuid.uuid4().hex}.csv"

    def _export():
        jira = JIRA(server=url, basic_auth=(email, api_token))
        log_rows, people = [], set()
        for issue in jira.enhanced_search_issues(f"worklogDate >= '{start_date}' AND worklogDate <= '{end_date}'", maxResults=0):
            if getattr(issue.fields, "assignee", None): people.add(issue.fields.assignee.displayName)
            for w in jira.worklogs(issue.id):
                if start_date <= w.started[:10] <= end_date:
                    people.add(w.author.displayName)
                    log_rows.append((w.author.displayName, w.started[:10], w.timeSpentSeconds / 3600))
        cols = pd.date_range(start_date, end_date).strftime("%Y-%m-%d").tolist()
        df = pd.DataFrame(log_rows, columns=["author", "date", "hours"])
        if not df.empty: df = df.pivot_table(index="author", columns="date", values="hours", aggfunc="sum", fill_value=0)
        df.reindex(index=sorted(people), columns=cols, fill_value=0).round(0).astype(int).to_csv(output_path)
        return output_path

    await asyncio.to_thread(_export)
    return output_path

async def func_otp_send_email(*, app_state: any, service: str, sender: str, email: str, otp: int) -> str:
    """Sends OTP code via configured email service (ses, resend, azure)."""
    import httpx
    import orjson
    import asyncio

    if service == "ses":
        if not app_state.client_ses: raise Exception("SES client not initialized")
        app_state.client_ses.send_email(Source=sender, Destination={"ToAddresses": [email]}, Message={"Subject": {"Data": "your otp code"}, "Body": {"Html": {"Data": str(otp)}}})
    elif service == "resend":
        headers = {"Authorization": f"Bearer {app_state.config_resend_key}", "Content-Type": "application/json"}
        payload = {"from": sender, "to": [email], "subject": "your otp code", "html": f"<p>Your OTP code is <strong>{otp}</strong>. It is valid for 10 minutes.</p>"}
        async with httpx.AsyncClient() as client:
            response = await client.post(app_state.config_resend_url, headers=headers, data=orjson.dumps(payload).decode("utf-8"))
            if response.status_code != 200: raise Exception(f"failed to send email: {response.text}")
    elif service == "azure":
        if not app_state.client_azure_email: raise Exception("azure email client not configured")
        message = {"senderAddress": sender, "recipients": {"to": [{"address": email}]}, "content": {"subject": "your otp code", "plainText": str(otp)}}
        await asyncio.to_thread(lambda: app_state.client_azure_email.begin_send(message).result())
    else:
        raise Exception(f"email service {service} not supported")
    return "done"

async def func_otp_send_mobile(*, app_state: any, service: str, mobile: str, otp: int, sns_template: dict = None) -> any:
    """Sends OTP code via configured mobile service (sns, fast2sms)."""
    import httpx

    if service == "sns":
        if not app_state.client_sns: raise Exception("SNS client not initialized")
        if sns_template:
            app_state.client_sns.publish(
                PhoneNumber=mobile,
                Message=sns_template["message"].replace("{otp}", str(otp)),
                MessageAttributes={
                    "AWS.SNS.SMS.SenderID": {"DataType": "String", "StringValue": sns_template["sender_id"]},
                    "AWS.MM.SMS.TemplateId": {"DataType": "String", "StringValue": sns_template["template_id"]},
                    "AWS.MM.SMS.EntityId": {"DataType": "String", "StringValue": sns_template["entity_id"]},
                    "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}
                }
            )
            return "done"
        else:
            app_state.client_sns.publish(PhoneNumber=mobile, Message=str(otp))
            return "done"
    elif service == "fast2sms":
        params = {"authorization": app_state.config_fast2sms_key, "route": "otp", "variables_values": str(otp), "numbers": mobile}
        async with httpx.AsyncClient() as client:
            response = await client.get(app_state.config_fast2sms_url, params=params)
            return response.json()
    else:
        raise Exception(f"mobile service {service} not supported")

async def func_postgres_groupby_read(*, app_state: any, table: str, col: str, limit: int, page: int, agg: str, a_col: str, order: str, filter: list) -> dict:
    """Executes a PostgreSQL GROUP BY query dynamically and returns the paginated results."""
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)) or not re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(col)) or (a_col != "*" and not re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(a_col))):
        raise Exception("invalid identifier")
    
    where_clause, values = await app_state.func_postgres_where_build(client_postgres=app_state.client_postgres, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, cache_postgres_schema=app_state.cache_postgres_schema, table=table, filter=filter, prefix="x.")
    bind_idx = len(values) + 1
    is_array = "[]" in (dt := app_state.cache_postgres_schema.get(table, {}).get(col, {}).get("datatype", "text").lower()) or "array" in dt
    agg_sql = f'{agg}(*)' if agg == "count" and a_col == "*" else f'{agg}("{a_col}")'
    order_sql = (("agg_val" if agg != "count" else "count(*)") if "count" in order else "item_col") + (" DESC" if "desc" in order else " ASC")
    q_col = f'"{col}"'
    sql = f'SELECT {"item_col" if is_array else "x."+q_col+" AS item_col"}, {agg_sql} AS agg_val FROM "{table}" x {f"CROSS JOIN LATERAL unnest(x."+q_col+") item_col" if is_array else ""} {where_clause} GROUP BY item_col ORDER BY {order_sql} LIMIT ${bind_idx} OFFSET ${bind_idx+1}'
    values.extend([limit + 1, (page - 1) * limit])
    
    async with app_state.client_postgres.acquire() as conn:
        rows = await conn.fetch(sql, *values)
        ol = [{"item": row["item_col"], "value": row["agg_val"]} for row in rows]
        return {"obj_list": ol[:limit], "has_next_page": len(ol) > limit}

async def func_blob_preview_urls_get(*, client_s3: any, client_azure_blob: any, config_azure_account_name: str, config_azure_account_key: str, config_blob_expire_sec_preview: int, service: str, urls: list) -> dict:
    """Generates presigned preview URLs for S3 or Azure blob URLs using robust parsing and unquoting."""
    import urllib.parse
    from datetime import datetime, timedelta, timezone
    from azure.storage.blob import BlobSasPermissions, generate_blob_sas
    if (service == "s3" and not client_s3) or (service == "azure" and not client_azure_blob):
        raise Exception("blob client not initialized")
    if service == "azure" and (not config_azure_account_name or not config_azure_account_key):
        raise Exception("azure storage credentials not configured")
    output = {}
    if service == "s3":
        for url in urls:
            if not url: continue
            parsed = urllib.parse.urlparse(url)
            host_parts = parsed.netloc.split(".")
            if host_parts[0] != "s3":
                bucket = host_parts[0]
                key = parsed.path.lstrip("/")
            else:
                parts = parsed.path.lstrip("/").split("/", 1)
                if len(parts) != 2: continue
                bucket, key = parts[0], parts[1]
            decoded_key = urllib.parse.unquote(key)
            presigned_url = client_s3.generate_presigned_url(ClientMethod='get_object', Params={'Bucket': bucket, 'Key': decoded_key}, ExpiresIn=config_blob_expire_sec_preview)
            output[url] = presigned_url
    elif service == "azure":
        for url in urls:
            if not url: continue
            parsed = urllib.parse.urlparse(url)
            parts = parsed.path.lstrip("/").split("/", 1)
            if len(parts) != 2: continue
            container, key = parts[0], parts[1]
            decoded_key = urllib.parse.unquote(key)
            sas_token = generate_blob_sas(account_name=config_azure_account_name, account_key=config_azure_account_key, container_name=container, blob_name=decoded_key, permission=BlobSasPermissions(read=True), expiry=datetime.now(timezone.utc) + timedelta(seconds=config_blob_expire_sec_preview))
            output[url] = f"https://{config_azure_account_name}.blob.core.windows.net/{container}/{decoded_key}?{sas_token}"
    return output

async def func_blob_delete_all(*, app_state: any, user_id: int, limit: int = 500) -> dict:
    """Fetches and deletes a batch of blobs for a user, marking them as deleted in the database."""
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    async with app_state.client_postgres.acquire() as conn:
        records = await conn.fetch("SELECT id, file_url, service FROM blob WHERE created_by_id = $1 AND deleted_at IS NULL LIMIT $2", user_id, limit + 1)
        if not records: return {"deleted_count": 0, "has_more": False}
        has_more = len(records) > limit
        process_records = records[:limit]
        s3_urls = [r["file_url"] for r in process_records if r["service"] == "s3"]
        azure_urls = [r["file_url"] for r in process_records if r["service"] == "azure"]
        if s3_urls: await app_state.func_blob_url_delete(app_state=app_state, service="s3", urls=s3_urls, user_id=user_id)
        if azure_urls: await app_state.func_blob_url_delete(app_state=app_state, service="azure", urls=azure_urls, user_id=user_id)
        ids_to_update = [r["id"] for r in process_records]
        await conn.execute("UPDATE blob SET deleted_at = NOW(), deleted_by_id = $1 WHERE id = ANY($2::bigint[])", user_id, ids_to_update)
    return {"deleted_count": len(process_records), "has_more": has_more}

async def func_converter_number(*, datatype: str, mode: str, x: str) -> any:
    """Encodes a string to an integer or decodes an integer to a string based on base-39 charset mapping."""
    type_limits = {"smallint": 2, "int": 5, "bigint": 11}
    charset = "abcdefghijklmnopqrstuvwxyz0123456789_-.@#"
    if datatype not in type_limits: raise ValueError(f"invalid type: {datatype}, allowed: {list(type_limits.keys())}")
    base = len(charset)
    max_len = type_limits[datatype]
    if mode == "encode":
        val_str = str(x)
        val_len = len(val_str)
        if val_len > max_len: raise ValueError(f"input too long {val_len} > {max_len}")
        result_num = val_len
        for char in val_str:
            char_idx = charset.find(char)
            if char_idx == -1: raise ValueError("invalid character in input")
            result_num = result_num * base + char_idx
        return result_num
    elif mode == "decode":
        try: num_val = int(x)
        except Exception: raise ValueError("invalid integer for decoding")
        decoded_chars = []
        while num_val > 0:
            num_val, reminder = divmod(num_val, base)
            decoded_chars.append(charset[reminder])
        return "".join(decoded_chars[::-1][1:]) if decoded_chars else ""
    else:
        raise ValueError(f"invalid mode: {mode}")

async def func_email_send(*, app_state: any, service: str, sender: str, to: list, subject: str, text: str, cc: list = None, bcc: list = None, reply_to: list = None) -> dict:
    """Sends a custom email via the specified service (ses, resend, azure)."""
    import asyncio
    import orjson

    if (service == "ses" and not app_state.client_ses) or (service == "resend" and not app_state.client_http) or (service == "azure" and not app_state.client_azure_email):
        raise Exception("email client not initialized")
    
    cc = cc or []
    bcc = bcc or []
    reply_to = reply_to or []

    message = None
    if service == "ses":
        params = {"Source": sender, "Destination": {"ToAddresses": to, "CcAddresses": cc, "BccAddresses": bcc}, "Message": {"Subject": {"Data": subject}, "Body": {"Text": {"Data": text}}}}
        if reply_to: params["ReplyToAddresses"] = reply_to
        response = app_state.client_ses.send_email(**params)
        message = {"id": response.get("MessageId")}
    elif service == "resend":
        headers = {"Authorization": f"Bearer {app_state.config_resend_key}", "Content-Type": "application/json"}
        payload = {"from": sender, "to": to, "subject": subject, "text": text}
        if cc: payload["cc"] = cc
        if bcc: payload["bcc"] = bcc
        if reply_to: payload["reply_to"] = reply_to
        response = await app_state.client_http.post(app_state.config_resend_url, headers=headers, content=orjson.dumps(payload))
        if response.status_code not in (200, 201): raise Exception(f"failed to send email: {response.text}")
        message = response.json()
    elif service == "azure":
        azure_message = {"senderAddress": sender, "recipients": {"to": [{"address": email} for email in to]}, "content": {"subject": subject, "plainText": text}}
        if cc: azure_message["recipients"]["cc"] = [{"address": email} for email in cc]
        if bcc: azure_message["recipients"]["bcc"] = [{"address": email} for email in bcc]
        if reply_to: azure_message["replyTo"] = [{"address": email} for email in reply_to]
        result = await asyncio.to_thread(lambda: app_state.client_azure_email.begin_send(azure_message).result())
        message = dict(result) if isinstance(result, dict) else {"id": getattr(result, "id", None), "status": getattr(result, "status", None)}
    else:
        raise Exception(f"email service {service} not supported")
    return message

async def func_blob_upload_file(*, app_state: any, service: str, container: str, files: list, user_id: int) -> dict:
    """Uploads a list of UploadFile objects to S3 or Azure and logs them in the database."""
    import uuid
    if not app_state.client_postgres or (service == "s3" and not app_state.client_s3) or (service == "azure" and not app_state.client_azure_blob):
        raise Exception("required postgres/blob client not initialized")
    if len(files) > app_state.config_blob_limit_upload:
        raise Exception(f"maximum {app_state.config_blob_limit_upload} files allowed")
    
    output = {}
    blob_list = []
    container_client = app_state.client_azure_blob.get_container_client(container) if service == "azure" else None
    
    for item in files:
        file_data = await item.read()
        if len(file_data) > app_state.config_blob_limit_size_kb * 1024:
            raise Exception(f"file size exceeds {app_state.config_blob_limit_size_kb}kb")
        ext = item.filename.split(".")[-1] if "." in item.filename else "bin"
        file_key = f"user_{user_id}/{uuid.uuid4().hex}.{ext}"
        if service == "s3":
            await app_state.client_s3.put_object(Bucket=container, Key=file_key, Body=file_data)
            file_url = f"https://{container}.s3.amazonaws.com/{file_key}"
        elif service == "azure":
            blob_client = container_client.get_blob_client(file_key)
            await blob_client.upload_blob(file_data)
            file_url = blob_client.url
        output[item.filename] = file_url
        blob_list.append({"created_by_id": user_id, "type": 1, "service": service, "file_url": file_url})
        
    if blob_list:
        await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_buffer_limit_default, mode="now", table="blob", obj_list=blob_list)
    return output

async def func_blob_upload_url(*, app_state: any, service: str, container: str, count: int, user_id: int) -> list:
    """Generates presigned upload URLs (S3 post fields or Azure SAS URLs) for client-side uploads and logs them in the database."""
    import uuid
    from datetime import datetime, timedelta, timezone
    from azure.storage.blob import BlobSasPermissions, generate_blob_sas

    if not app_state.client_postgres or (service == "s3" and not app_state.client_s3):
        raise Exception("required postgres/blob client not initialized")
    if service == "azure" and (not app_state.config_azure_account_name or not app_state.config_azure_account_key):
        raise Exception("azure storage credentials not configured")
    if count > app_state.config_blob_limit_upload:
        raise Exception(f"maximum {app_state.config_blob_limit_upload} allowed")
    
    output = []
    blob_list = []
    
    for _ in range(count):
        file_key = f"user_{user_id}/{uuid.uuid4().hex}.bin"
        if service == "s3":
            presigned_post = app_state.client_s3.generate_presigned_post(Bucket=container, Key=file_key, ExpiresIn=app_state.config_blob_expire_sec_upload, Conditions=[["content-length-range", 1, app_state.config_blob_limit_size_kb * 1024]])
            file_url = f"https://{container}.s3.{app_state.config_aws_s3_region_name}.amazonaws.com/{file_key}"
            output.append({"upload_url": presigned_post["url"], **presigned_post["fields"], "file_url": file_url})
        elif service == "azure":
            sas_token = generate_blob_sas(account_name=app_state.config_azure_account_name, account_key=app_state.config_azure_account_key, container_name=container, blob_name=file_key, permission=BlobSasPermissions(write=True, create=True), expiry=datetime.now(timezone.utc) + timedelta(seconds=app_state.config_blob_expire_sec_upload))
            sas_url = f"https://{app_state.config_azure_account_name}.blob.core.windows.net/{container}/{file_key}?{sas_token}"
            file_url = f"https://{app_state.config_azure_account_name}.blob.core.windows.net/{container}/{file_key}"
            output.append({"upload_url": sas_url, "key": file_key, "file_url": file_url})
        blob_list.append({"created_by_id": user_id, "type": 2, "service": service, "file_url": file_url})
        
    if blob_list:
        await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_buffer_limit_default, mode="now", table="blob", obj_list=blob_list)
    return output

async def func_redis_import(*, client_redis: any, config_redis_cache_ttl_sec: int, mode: str, file: any) -> str:
    """Imports or deletes keys in Redis in batches from a CSV file."""
    import orjson
    if not client_redis: raise Exception("redis client not initialized")
    count = 0; limit_batch = 5000
    async for ol in func_api_file_to_chunks(upload_file=file, chunk_size=limit_batch):
        if mode == "create":
            if sorted(list(ol[0].keys())) != sorted(["key", "value"]): raise Exception("CSV format error: requires 'key' and 'value'")
            async with client_redis.pipeline(transaction=False) as pipe:
                for item in ol:
                    val = orjson.dumps(item["value"]).decode("utf-8")
                    if config_redis_cache_ttl_sec: pipe.setex(item["key"], config_redis_cache_ttl_sec, val)
                    else: pipe.set(item["key"], val)
                await pipe.execute()
        elif mode == "delete":
            if list(ol[0].keys()) != ["key"]: raise Exception("CSV format error: requires 'key' column")
            async with client_redis.pipeline(transaction=False) as pipe:
                pipe.delete(*[item["key"] for item in ol])
                await pipe.execute()
        count += len(ol)
    return f"{count} rows processed"

async def func_mongodb_import(*, client_mongodb: any, mode: str, database: str, table: str, file: any) -> str:
    """Imports, updates, or deletes records in MongoDB from a CSV upload file in batches."""
    from pymongo import UpdateOne, DeleteOne
    if not client_mongodb: raise Exception("mongodb client not initialized")
    
    count = 0
    limit_batch = 5000
    collection = client_mongodb[database][table]
    
    def _mongodb_import_id(item, mode_name):
        if "id" not in item and "_id" not in item: raise Exception(f"CSV format error: MongoDB {mode_name} requires 'id' or '_id' column")
        oid = item.get("id") or item.get("_id")
        if not oid: raise Exception(f"CSV format error: MongoDB {mode_name} requires non-empty 'id' or '_id'")
        return oid

    async for ol in func_api_file_to_chunks(upload_file=file, chunk_size=limit_batch):
        if not ol: continue
        if mode == "create":
            await collection.insert_many(ol)
        elif mode == "update":
            operations = []
            for item in ol:
                oid = _mongodb_import_id(item, mode)
                item = dict(item)
                item.pop("id", None); item.pop("_id", None)
                operations.append(UpdateOne({"_id": oid}, {"$set": item}))
            await collection.bulk_write(operations, ordered=True)
        elif mode == "delete":
            operations = [DeleteOne({"_id": _mongodb_import_id(item, mode)}) for item in ol]
            await collection.bulk_write(operations, ordered=True)
        count += len(ol)
    return f"{count} rows processed"

async def func_blob_containers_read(*, client_s3: any, client_azure_blob: any, service: str) -> list:
    """Lists names of all S3 buckets or Azure containers for the initialized client."""
    if (service == "s3" and not client_s3) or (service == "azure" and not client_azure_blob):
        raise Exception("blob client not initialized")
    if service == "s3":
        res = await client_s3.list_buckets()
        return [b["Name"] for b in res.get("Buckets", [])]
    elif service == "azure":
        output = []
        async for c in client_azure_blob.list_containers():
            output.append(c.name)
        return output
    raise Exception(f"service {service} not supported")

async def func_blob_container_ops(*, client_s3: any, client_s3_resource: any, client_azure_blob: any, config_aws_s3_region_name: str, service: str, container: str, mode: str) -> any:
    """Creates, makes public, empties, or deletes S3 buckets or Azure Blob containers."""
    if (service == "s3" and ((mode == "empty" and not client_s3_resource) or (mode != "empty" and not client_s3))) or (service == "azure" and not client_azure_blob):
        raise Exception("blob client not initialized")
    
    res = None
    if service == "s3":
        if mode == "create":
            res = await client_s3.create_bucket(Bucket=container, CreateBucketConfiguration={"LocationConstraint": config_aws_s3_region_name})
        elif mode == "public":
            await client_s3.put_public_access_block(Bucket=container, PublicAccessBlockConfiguration={"BlockPublicAcls": False, "IgnorePublicAcls": False, "BlockPublicPolicy": False, "RestrictPublicBuckets": False})
            res = await client_s3.put_bucket_policy(Bucket=container, Policy="""{"Version":"2012-10-17","Statement":[{"Sid":"PublicRead","Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":["arn:aws:s3:::bucket_name/*"]}]}""".replace("bucket_name", container))
        elif mode == "empty":
            res = client_s3_resource.Bucket(container).objects.all().delete()
        elif mode == "delete":
            res = await client_s3.delete_bucket(Bucket=container)
    elif service == "azure":
        from azure.storage.blob import PublicAccess
        if mode == "create":
            await client_azure_blob.create_container(container)
            res = {"service": service, "mode": mode, "container": container}
        elif mode == "public":
            container_client = client_azure_blob.get_container_client(container)
            await container_client.set_container_access_policy(signed_identifiers={}, public_access=PublicAccess.Blob)
            res = {"service": service, "mode": mode, "container": container}
        elif mode == "empty":
            container_client = client_azure_blob.get_container_client(container)
            blobs = [blob.name async for blob in container_client.list_blobs()]
            for i in range(0, len(blobs), 256):
                delete_responses = await container_client.delete_blobs(*blobs[i:i + 256], delete_snapshots="include")
                if hasattr(delete_responses, "__aiter__"):
                    async for _ in delete_responses: pass
            res = {"service": service, "mode": mode, "container": container, "deleted": len(blobs)}
        elif mode == "delete":
            await client_azure_blob.delete_container(container)
            res = {"service": service, "mode": mode, "container": container}
        else:
            raise Exception(f"mode {mode} not supported for azure")
    return res

async def func_mssql_query_runner_read_export(*, client_mssql: any, config_query_runner_export_limit: int, sql: str) -> any:
    """Runs a read-only MSSQL query and yields CSV lines up to the configured export limit."""
    import re
    import asyncio
    if not client_mssql: raise Exception("MSSQL client not initialized")
    ql = sql.lower().strip().lstrip("(").strip()
    if not ql.startswith(("select", "with")): raise Exception("read mode restricted")
    if re.search(r"\b(insert|update|delete|merge|drop|alter|create|truncate|exec|execute|into)\b", ql): raise Exception("read mode restricted")
    limit = config_query_runner_export_limit

    async def _iter():
        for attempt in range(3):
            try:
                async with client_mssql.acquire() as conn:
                    cursor = await conn.cursor()
                    await cursor.execute(sql)
                    columns = [column[0] for column in cursor.description]
                    yield ",".join(columns) + "\n"
                    count = 0
                    while True:
                        rows = await cursor.fetchmany(min(500, limit - count))
                        if not rows: break
                        for row in rows:
                            yield ",".join([f"\"{str(v).replace(chr(34), chr(34)*2)}\"" if v is not None else "" for v in row]) + "\n"
                        count += len(rows)
                        if count >= limit: break
                    return
            except Exception as e:
                if "08S01" in str(e) and attempt < 2:
                    await asyncio.sleep(0.5)
                    continue
                raise e

    return _iter()

async def func_mssql_query_runner_read(*, client_mssql: any, config_query_runner_read_limit: int, sql: str) -> list:
    """Runs a read-only MSSQL query and returns matching records up to the configured limit."""
    import re
    import asyncio

    if not client_mssql: raise Exception("MSSQL client not initialized")
    ql = sql.lower().strip().lstrip("(").strip()
    if not ql.startswith(("select", "with")): raise Exception("read mode restricted")
    if re.search(r"\b(insert|update|delete|merge|drop|alter|create|truncate|exec|execute|into)\b", ql): raise Exception("read mode restricted")
    limit = config_query_runner_read_limit
    for attempt in range(3):
        try:
            async with client_mssql.acquire() as conn:
                cursor = await conn.cursor()
                await cursor.execute(sql)
                columns = [column[0] for column in cursor.description]
                result = []
                while len(result) < limit:
                    rows = await cursor.fetchmany(min(500, limit - len(result)))
                    if not rows: break
                    result.extend(dict(zip(columns, row)) for row in rows)
                return result
        except Exception as e:
            if "08S01" in str(e) and attempt < 2:
                await asyncio.sleep(0.5)
                continue
            raise e

async def func_mssql_query_runner_write(*, client_mssql: any, sql: str) -> str:
    """Runs a write SQL query against the MSSQL instance and commits the transaction."""
    import asyncio

    if not client_mssql: raise Exception("MSSQL client not initialized")
    ql = sql.lower().strip().lstrip("(").strip()
    if ql.startswith(("select", "with")): raise Exception("read SQL must use /admin/mssql-query-runner-read")
    for attempt in range(3):
        try:
            async with client_mssql.acquire() as conn:
                cursor = await conn.cursor()
                await cursor.execute(sql)
                await conn.commit()
                return "done"
        except Exception as e:
            if "08S01" in str(e) and attempt < 2:
                await asyncio.sleep(0.5)
                continue
            raise e

async def func_postgres_query_runner_read(*, client_postgres: any, config_query_runner_read_limit: int, sql: str) -> list:
    """Runs a read-only PostgreSQL SELECT/WITH query and returns row mappings up to the configured limit."""
    sql = str(sql or "").strip().rstrip(";").strip()
    if not sql: raise Exception("SQL is required")
    if ";" in sql: raise Exception("Only one SQL statement is allowed")
    if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("Only SELECT/WITH queries are supported")
    if not client_postgres: raise Exception("postgres client not initialized")
    timeout_sec = 30
    async with client_postgres.acquire() as conn:
        async with conn.transaction(readonly=True):
            await conn.execute(f"SET LOCAL statement_timeout = '{timeout_sec * 1000}ms'")
            stmt = await conn.prepare(f"SELECT * FROM ({sql}) AS postgres_query LIMIT $1")
            records = await stmt.fetch(config_query_runner_read_limit, timeout=timeout_sec)
    return [dict(row) for row in records]

async def func_postgres_query_runner_read_export(*, client_postgres: any, config_query_runner_export_limit: int, sql: str) -> any:
    """Runs a read-only PostgreSQL SELECT/WITH query and yields CSV chunks up to the configured export limit."""
    import io
    import csv

    sql = str(sql or "").strip().rstrip(";").strip()
    if not sql: raise Exception("SQL is required")
    if ";" in sql: raise Exception("Only one SQL statement is allowed")
    if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("Only SELECT/WITH queries are supported")
    if not client_postgres: raise Exception("postgres client not initialized")
    timeout_sec = 30

    async def _iter():
        async with client_postgres.acquire() as conn:
            async with conn.transaction(readonly=True):
                await conn.execute(f"SET LOCAL statement_timeout = '{timeout_sec * 1000}ms'")
                stmt = await conn.prepare(f"SELECT * FROM ({sql}) AS postgres_query LIMIT $1")
                columns = [attr.name for attr in stmt.get_attributes()]
                buffer = io.StringIO()
                writer = csv.writer(buffer)
                writer.writerow(columns)
                yield buffer.getvalue()
                buffer.seek(0); buffer.truncate(0)
                async for record in stmt.cursor(config_query_runner_export_limit, prefetch=250, timeout=timeout_sec):
                    writer.writerow([record[column] for column in columns])
                    yield buffer.getvalue()
                    buffer.seek(0); buffer.truncate(0)

    return _iter()

async def func_postgres_query_runner_write(*, client_postgres: any, sql: str) -> str:
    """Runs a write SQL query against the PostgreSQL instance and returns the result command tag."""
    if not client_postgres: raise Exception("postgres client not initialized")
    ql = sql.lower().strip().lstrip("(").strip()
    if ql.startswith(("select", "with", "explain", "show", "describe")): raise Exception("read SQL must use /admin/postgres-query-runner-read")
    if "returning" in ql: raise Exception("RETURNING is not allowed in write mode")
    async with client_postgres.acquire() as conn:
        result = await conn.execute(sql, timeout=15)
    return result

async def func_postgres_map_column(*, client_postgres: any, config_sql: str, is_json_value: int = 0) -> dict:
    """Execute a mapping SQL query and return a dictionary from the first two columns."""
    if not config_sql: return {}
    async with client_postgres.acquire() as conn:
        rows = await conn.fetch(config_sql)
    if is_json_value != 1: return {r[0]: r[1] for r in rows}
    import orjson
    output = {}
    for r in rows:
        value = r[1]
        if isinstance(value, (str, bytes, bytearray)): value = orjson.loads(value)
        output[r[0]] = value
    return output

async def func_postgres_import(*, app_state: any, mode: str, table: str, file: any) -> str:
    """Imports, updates, or deletes records in PostgreSQL from a CSV upload file in batches."""
    if not app_state.client_postgres: raise Exception("postgres client not initialized")
    if mode == "delete" and table == "users" and app_state.config_is_enable_user_delete != 1: raise Exception("users hard delete disabled")
    count = 0
    async with app_state.client_postgres.acquire() as conn:
        async with conn.transaction():
            async for ol in func_api_file_to_chunks(upload_file=file, chunk_size=5000):
                if not ol: continue
                if mode in ("update", "delete") and any("id" not in obj for obj in ol): raise Exception(f"CSV format error: Postgres {mode} requires 'id' column")
                if mode == "create":
                    await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=conn, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, cache_postgres_buffer_create=app_state.cache_postgres_buffer_create, config_regex=app_state.config_regex, buffer_limit=app_state.config_buffer_limit_default, mode="now", table=table, obj_list=ol)
                elif mode == "update":
                    await app_state.func_postgres_update(client_postgres=app_state.client_postgres, client_postgres_conn=conn, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=app_state.cache_postgres_schema, config_regex=app_state.config_regex, table=table, obj_list=ol, created_by_id=None)
                elif mode == "delete":
                    await app_state.func_postgres_delete(client_postgres=app_state.client_postgres, client_postgres_conn=conn, cache_postgres_schema=app_state.cache_postgres_schema, table=table, ids=[obj["id"] for obj in ol], created_by_id=None)
                count += len(ol)
    return f"{count} rows processed"

async def func_postgres_serialize(*, client_postgres: any, client_password_hasher: any, cache_postgres_schema: dict, table: str, obj_list: list, is_base: int) -> list:
    """Serialize Python objects (JSON, Arrays, Geog) to PostgreSQL compatible formats using schema-aware injection."""
    import orjson
    if table not in cache_postgres_schema: return obj_list
    output_list, schema = [], cache_postgres_schema[table]
    def normalize_dtype(t):
        t = str(t).lower().strip()
        array_alias_map = {
            "_int2": "smallint[]",
            "_int4": "integer[]",
            "_int8": "bigint[]",
            "_float4": "real[]",
            "_float8": "double precision[]",
            "_numeric": "numeric[]",
            "_bool": "boolean[]",
            "_text": "text[]",
            "_varchar": "character varying[]",
            "_bpchar": "character[]",
            "_date": "date[]",
            "_timestamp": "timestamp without time zone[]",
            "_timestamptz": "timestamp with time zone[]",
        }
        return array_alias_map.get(t, t)
    def cast_val(v, t):
        t = normalize_dtype(t)
        vs = str(v).strip()
        if not vs or vs.lower() == "null": return None
        if "geography" in t or "geometry" in t: return v
        if "bool" in t:
            bool_map = {
                "true": True, "1": True, "yes": True, "on": True, "ok": True, "t": True, "y": True,
                "false": False, "0": False, "no": False, "off": False, "f": False, "n": False,
            }
            key = vs.lower()
            if key not in bool_map: raise ValueError(f"invalid boolean value: {v}")
            return bool_map[key]
        if any(x in t for x in ("int", "serial", "bigint")): return int(vs)
        if any(x in t for x in ("numeric", "float", "double", "real")): return float(vs)
        if "timestamp" in t:
            from datetime import datetime
            return datetime.fromisoformat(vs.replace("Z", "+00:00")) if isinstance(v, str) else v
        if "date" in t:
            from datetime import date
            return date.fromisoformat(vs) if isinstance(v, str) else v
        return v
    def array_val(v, base_dtype):
        if isinstance(v, (list, tuple)): return [cast_val(x, base_dtype) for x in v]
        v_arr = str(v).strip().strip("{}")
        return [cast_val(x.strip(), base_dtype) for x in v_arr.split(",")] if v_arr else []
    def serialize_val(val, dtype):
        dtype = normalize_dtype(dtype)
        is_json, is_array = "json" in dtype, "[]" in dtype or "array" in dtype
        base_dtype = dtype.replace("[]", "").replace("array", "").strip()
        if is_json:
            if is_base == 1:
                return orjson.dumps(val).decode("utf-8") if not isinstance(val, str) else val
            if isinstance(val, str):
                val_str = val.strip()
                return orjson.loads(val_str) if val_str.startswith(("{", "[")) else val_str
            return val
        if is_array:
            return array_val(val, base_dtype)
        if is_base != 1 and "bytea" in dtype:
            return val.encode() if isinstance(val, str) else val
        return cast_val(val, dtype)
    for item in obj_list:
        new_item = {}
        for col, val in item.items():
            if table == "users" and col == "password" and val:
                val = client_password_hasher.hash(str(val))
            if col not in schema:
                if col == "id":
                    new_item[col] = val
                    continue
                raise Exception(f"column '{col}' does not exist in table '{table}'")
            if val is None:
                new_item[col] = val
                continue
            new_item[col] = serialize_val(val, schema[col]["datatype"])
        output_list.append(new_item)
    return output_list

async def func_postgres_where_build(*, client_postgres: any, client_password_hasher: any, func_postgres_serialize: callable, cache_postgres_schema: dict, table: str, filter: list, prefix: str = "") -> tuple:
    """Build a SQL WHERE clause with support for recursion, logical operators (_or, _and), flat SQL strings, and explicit operator syntax."""
    import re, orjson
    values = []
    filter_pattern = r'^((?:"[^"]+")|[a-zA-Z_][a-zA-Z0-9_]*)\s+(is\s+not\s+distinct\s+from|is\s+distinct\s+from|is\s+not|not\s+in|>=|<=|==|!=|<>|~\*|=|>|<|eq|neq|gt|lt|gte|lte|is|in|between|like|ilike|~|contains|exists|overlap|any|point)\s+(.*)$'
    value_ops = {"=":"=","==":"=","eq":"=","!=":"!=","<>":"!=","neq":"!=","!=": "!=", ">":">","gt":">","<":"<","lt":"<",">=":">=","gte":">=","<=":"<=","lte":"<=","is":"IS","is not":"IS NOT","in":"IN","not in":"NOT IN","between":"BETWEEN","is distinct from":"IS DISTINCT FROM","is not distinct from":"IS NOT DISTINCT FROM"}
    string_ops = {"like":"LIKE","ilike":"ILIKE","~":"~","~*":"~*"}
    table_schema = cache_postgres_schema.get(table, {})
    def normalize_filter_value(operator, raw_val):
        raw_val = raw_val.strip().strip("'").strip('"').strip("(").strip(")")
        return raw_val.replace(" AND ", "|").replace(",", "|") if operator in ("between", "in", "not in", "overlap", "contains") else raw_val
    def parse_filter_item(item):
        match = re.match(filter_pattern, item.strip(), re.IGNORECASE)
        if not match: return None
        col, operator, raw_val = match.groups()
        operator = operator.lower()
        return {col.strip('"'): f"{operator},{normalize_filter_value(operator, raw_val)}"}
    def parse_filter_list(filter_list):
        converted_filters = {}
        def add_parsed_filter(parsed):
            if not parsed: return
            key = next(iter(parsed))
            if key in converted_filters:
                converted_filters.setdefault("_and", []).append({key: converted_filters.pop(key)})
                converted_filters["_and"].append(parsed)
            elif "_and" in converted_filters:
                converted_filters["_and"].append(parsed)
            else:
                converted_filters.update(parsed)
        for item in filter_list:
            if isinstance(item, dict):
                converted_filters.update(item)
                continue
            if not isinstance(item, str): continue
            or_parts = re.split(r"\s+OR\s+", item, flags=re.IGNORECASE)
            if len(or_parts) > 1:
                sub_or = [parsed for part in or_parts if (parsed := parse_filter_item(part))]
                if sub_or: converted_filters.setdefault("_and", []).append({"_or": sub_or})
                continue
            parsed = parse_filter_item(item)
            add_parsed_filter(parsed)
        return converted_filters
    def bind_next(val):
        bind_idx = len(values) + 1
        values.append(val)
        return bind_idx
    def validate_filter_column(filter_key):
        if filter_key not in table_schema: raise Exception(f"invalid filter column: {filter_key} for table: {table}")
        if not re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(filter_key)): raise Exception(f"invalid identifier {filter_key}")
    def allowed_operators(datatype, is_json, is_array):
        allowed_ops = list(value_ops.keys())
        if any(x in datatype for x in ("text", "char", "varchar")): allowed_ops += list(string_ops.keys())
        if is_array: allowed_ops += ["contains", "overlap", "any"]
        if is_json: allowed_ops += ["contains", "exists"]
        return allowed_ops
    async def serialize_filter_many(col, val_list, is_base_type=0, schema_override=None):
        obj_list = [{col: None if str(val).lower() == "null" else val} for val in val_list]
        serialized = await func_postgres_serialize(client_postgres=client_postgres, client_password_hasher=client_password_hasher, cache_postgres_schema=schema_override or cache_postgres_schema, table=table, obj_list=obj_list, is_base=is_base_type)
        return [item[col] for item in serialized]
    async def serialize_filter(col, val, is_base_type=0):
        return (await serialize_filter_many(col, [val], is_base_type))[0]
    async def serialize_filter_value(filter_key, operator, raw_val, datatype, is_json, is_array):
        if operator == "contains":
            if is_json:
                if "|" in raw_val and not (raw_val.startswith("{") or raw_val.startswith("[")):
                    parts = raw_val.split("|"); k, vr, t = parts[0], parts[1], parts[2].lower() if len(parts) > 2 else "str"
                    v = int(vr) if t == "int" else (vr.lower() == "true" if t == "bool" else float(vr) if t == "float" else vr)
                    return orjson.dumps({k: v}).decode('utf-8')
                try: return orjson.dumps(orjson.loads(raw_val)).decode('utf-8')
                except: return raw_val
            if is_array:
                parts = raw_val.split("|"); elem_type = datatype.replace("[]", "").replace("array", "").replace("int4", "int").replace("_", "").strip()
                fake_schema = {table: {**cache_postgres_schema.get(table, {}), filter_key: {"datatype": elem_type}}}
                return await serialize_filter_many(filter_key, [x.strip() for x in parts], 1, fake_schema)
            return await serialize_filter(filter_key, raw_val)
        if operator == "overlap":
            fake_schema = {table: {**cache_postgres_schema.get(table, {}), filter_key: {"datatype": datatype.replace("[]", "").replace("array", "").strip()}}}
            return await serialize_filter_many(filter_key, [x.strip() for x in raw_val.split("|")], 1, fake_schema)
        if operator in ("in", "not in", "between"):
            return await serialize_filter_many(filter_key, [x.strip() for x in raw_val.split("|")], 1 if is_array else 0)
        if operator == "any":
            fake_schema = {table: {**cache_postgres_schema.get(table, {}), filter_key: {"datatype": datatype.replace("[]", "").replace("array", "").strip()}}}
            return (await serialize_filter_many(filter_key, [raw_val], 1, fake_schema))[0]
        return await serialize_filter(filter_key, raw_val, 1 if is_json and operator == "exists" else 0)
    def build_condition_sql(filter_key, operator, serialized_val, is_json):
        if serialized_val is None:
            return f'{prefix}"{filter_key}" {value_ops[operator]} NULL' if operator in ("is", "is not", "is distinct from", "is not distinct from") else None
        if operator == "contains":
            bind_idx = bind_next(serialized_val)
            return f'{prefix}"{filter_key}" @> ${bind_idx}{"::jsonb" if is_json else ""}'
        if operator == "exists":
            bind_idx = bind_next(serialized_val)
            return f'{prefix}"{filter_key}" ? ${bind_idx}'
        if operator == "overlap":
            bind_idx = bind_next(serialized_val)
            return f'{prefix}"{filter_key}" && ${bind_idx}'
        if operator == "any":
            bind_idx = bind_next(serialized_val)
            return f'${bind_idx} = ANY({prefix}"{filter_key}")'
        if operator in ("in", "not in"):
            bind_idx = len(values) + 1
            placeholders = [f"${bind_idx + i}" for i in range(len(serialized_val))]
            values.extend(serialized_val)
            return f'{prefix}"{filter_key}" {value_ops[operator]} ({",".join(placeholders)})'
        if operator == "between":
            bind_idx = len(values) + 1
            values.extend(serialized_val)
            return f'{prefix}"{filter_key}" BETWEEN ${bind_idx} AND ${bind_idx+1}'
        bind_idx = bind_next(serialized_val)
        return f'{prefix}"{filter_key}" {(value_ops.get(operator) or string_ops.get(operator))} ${bind_idx}'
    async def build_filter(filter_obj, is_root=True):
        if not filter_obj: return ""
        if isinstance(filter_obj, list) and is_root:
            filter_obj = parse_filter_list(filter_obj)
        conditions = []
        for filter_key, expression in filter_obj.items():
            if filter_key in ("_or", "_and"):
                if not isinstance(expression, list): raise Exception(f"{filter_key} must be a list of objects")
                inner_conditions = []
                for sub_filter in expression:
                    sub_where = await build_filter(sub_filter, is_root=False)
                    if sub_where: inner_conditions.append(sub_where)
                if inner_conditions:
                    logic_op = " OR " if filter_key == "_or" else " AND "
                    joined_conditions = (f' {logic_op} ').join(inner_conditions)
                    conditions.append(joined_conditions if filter_key == "_and" and len(inner_conditions) == 1 else f"({joined_conditions})")
                continue
            validate_filter_column(filter_key)
            clean_expr = str(expression)
            if clean_expr.lower().startswith("=,"): clean_expr = clean_expr[2:]
            if clean_expr.lower().startswith("point,"):
                _, coords = clean_expr.split(",", 1)
                lon, lat, min_meter, max_meter = [float(x) for x in coords.split("|")]
                bind_idx = len(values) + 1
                conditions.append(f'ST_Distance({prefix}"{filter_key}", ST_Point(${bind_idx}, ${bind_idx+1})::geography) BETWEEN ${bind_idx+2} AND ${bind_idx+3}')
                values.extend([lon, lat, min_meter, max_meter]); continue
            if "," not in str(expression): raise Exception(f"invalid expression for {filter_key}: {expression}. Expected 'operator,value'")
            datatype = table_schema.get(filter_key, {}).get("datatype", "text").lower()
            is_json, is_array = "json" in datatype, "[]" in datatype or "array" in datatype
            operator, raw_val = [x.strip() for x in expression.split(",", 1)]
            operator = operator.lower()
            if operator not in allowed_operators(datatype, is_json, is_array): raise Exception(f"invalid operator: {operator} for {filter_key}")
            serialized_val = await serialize_filter_value(filter_key, operator, raw_val, datatype, is_json, is_array)
            condition_sql = build_condition_sql(filter_key, operator, serialized_val, is_json)
            if condition_sql: conditions.append(condition_sql)
        prefix_sql = "WHERE " if is_root else ""
        return (prefix_sql + " AND ".join(conditions)) if conditions else ""
    where_sql = await build_filter(filter)
    return where_sql, values

async def func_postgres_relation(*, client_postgres: any, client_postgres_conn: any = None, obj_list: list, relation: list, config_sql_read_relation_fetch_limit_max: int) -> list:
    """Standardized relationship logic: handles both aggregates (count, sum, etc) and associations (fetching rows) from source to target."""
    if not relation or not obj_list: return obj_list
    import re
    from collections import defaultdict
    relations = relation if isinstance(relation, (list, tuple)) else [relation]
    for rel_str in relations:
        if not rel_str: continue
        parts = [p.strip() for p in rel_str.split(",", 4)]
        if len(parts) < 5: raise Exception("relation must have 5 parts: source_col,target_table,target_col,op,val")
        source_col, target_table, target_col, op, val = parts
        op_parts = op.split("|")
        op_main = op_parts[0].lower()
        for p in (target_table, op_main):
             if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", p): raise Exception(f"invalid identifier in relation: {p}")
        for p in (source_col, target_col):
             if not re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", p): raise Exception(f"invalid identifier in relation: {p}")
        if val != "*" and not all(re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", v.strip()) for v in val.split(",")): raise Exception(f"invalid value in relation: {val}")
        if any(source_col not in r for r in obj_list): raise Exception(f"relation source column missing from selected columns: {source_col}")
        source_ids = {r.get(source_col) for r in obj_list if r.get(source_col) is not None}
        if not source_ids: continue
        client = client_postgres_conn or client_postgres
        if op_main in ("count", "sum", "avg", "min", "max"):
            val_sql = "*" if val == "*" else f'"{val}"'
            sql = f'SELECT "{target_col}" AS id, {op_main}({val_sql}) AS value FROM "{target_table}" WHERE "{target_col}" = ANY($1) GROUP BY "{target_col}";'
            rows = await client.fetch(sql, list(source_ids))
            mapping = {str(r["id"]): r["value"] for r in rows}
            for obj in obj_list:
                sid = str(obj.get(source_col))
                obj[f"{target_table}_{op_main}"] = mapping.get(sid, 0 if op_main == "count" else None)
        elif op_main == "fetch":
            if len(op_parts) < 2 or not op_parts[1].isdigit(): raise Exception("explicit limit required in relation fetch (e.g. fetch|10)")
            custom_limit = int(op_parts[1])
            if custom_limit > config_sql_read_relation_fetch_limit_max: raise Exception(f"relation fetch limit {custom_limit} exceeds maximum allowed: {config_sql_read_relation_fetch_limit_max}")
            cols_sql = "*" if val == "*" else ",".join([f'"{v.strip()}"' for v in val.split(",")])
            if val != "*" and "id" not in val.split(",") and target_col != "id": cols_sql += f',"{target_col}"'
            sql = f'SELECT * FROM (SELECT {cols_sql}, "{target_col}" AS relation_id, ROW_NUMBER() OVER(PARTITION BY "{target_col}" ORDER BY id DESC) as rn FROM "{target_table}" WHERE "{target_col}" = ANY($1)) t WHERE rn <= $2'
            rows = await client.fetch(sql, list(source_ids), custom_limit)
            mapping = defaultdict(list)
            for r in rows:
                d = dict(r)
                d.pop("rn", None); rid = str(d.pop("relation_id", None))
                mapping[rid].append(d)
            for obj in obj_list:
                sid = str(obj.get(source_col))
                if target_col == "id": obj[target_table] = mapping[sid][0] if mapping[sid] else None
                else: obj[target_table] = mapping[sid]
        else: raise Exception(f"invalid operator: {op}")
    return obj_list

async def func_postgres_create(*, client_postgres: any, client_postgres_conn: any, client_password_hasher: any, func_postgres_serialize: callable, func_regex_check: callable, cache_postgres_schema: dict, cache_postgres_buffer_create: dict, config_regex: dict, buffer_limit: int, mode: str, table: str, obj_list: list) -> any:
    """Create PostgreSQL records with support for buffering, batch insertion, and dynamic serialization."""
    import re, orjson
    limit_chunk = 5000
    async def insert_serialized(tbl, serialized_list, connection=None):
        columns = [c for c in serialized_list[0] if re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(c)) or (_ for _ in ()).throw(Exception(f"invalid identifier {c}"))]
        cols_sql = ",".join([f'"{c}"' for c in columns])
        if len(serialized_list) == 1:
            placeholders = ",".join([f"${i+1}" for i in range(len(columns))])
            sql = f'INSERT INTO "{tbl}" ({cols_sql}) VALUES ({placeholders}) RETURNING id;'
            args = [serialized_list[0][c] for c in columns]
            if connection: ids = await connection.fetch(sql, *args)
            elif client_postgres_conn: ids = await client_postgres_conn.fetch(sql, *args)
            else:
                async with client_postgres.acquire() as conn: ids = await conn.fetch(sql, *args)
        else:
            schema = cache_postgres_schema.get(tbl, {})
            col_list = ",".join([f'"{c}"' for c in columns])
            def_list = ",".join([f'"{c}" jsonb' for c in columns])
            cast_parts = []
            for c in columns:
                col_dtype = schema.get(c, {}).get("datatype", "text")
                if "[]" in col_dtype:
                    cast_parts.append(f'(SELECT ARRAY(SELECT jsonb_array_elements_text("{c}")))::{col_dtype}')
                elif "jsonb" in col_dtype:
                    cast_parts.append(f'"{c}"::{col_dtype}')
                else:
                    cast_parts.append(f'("{c}"->>0)::{col_dtype}')
            cast_list = ",".join(cast_parts)
            all_ids = []
            async def _execute_bulk(connection):
                async with connection.transaction():
                    for i in range(0, len(serialized_list), limit_chunk):
                        batch = serialized_list[i : i + limit_chunk]
                        sql = f'INSERT INTO "{tbl}" ({col_list}) SELECT {cast_list} FROM jsonb_to_recordset($1::jsonb) AS x({def_list}) RETURNING id'
                        ids_batch = await connection.fetch(sql, orjson.dumps(batch, default=str).decode('utf-8'))
                        all_ids.extend([dict(r) for r in ids_batch])
            if connection:
                await _execute_bulk(connection)
            elif client_postgres_conn:
                await _execute_bulk(client_postgres_conn)
            else:
                async with client_postgres.acquire() as conn:
                    await _execute_bulk(conn)
            ids = all_ids
        return [r["id"] for r in ids] if ids and "id" in ids[0] else "created"
    async def serialize_batches():
        for i in range(0, len(obj_list), limit_chunk):
            batch = obj_list[i:i+limit_chunk]
            await func_regex_check(config_regex=config_regex, obj_list=batch)
            yield await func_postgres_serialize(client_postgres=client_postgres, client_password_hasher=client_password_hasher, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=batch, is_base=0 if len(batch) > 1 else 1)
    if mode not in ("now", "buffer", "flush"): raise Exception(f"invalid mode: {mode}")
    if mode == "flush":
        for key, buffer_list in list(cache_postgres_buffer_create.items()):
            if buffer_list:
                parts = key.split("|")
                tbl = parts[0]
                await insert_serialized(tbl, buffer_list)
                cache_postgres_buffer_create[key] = []
        return "flushed"
    if not obj_list: raise Exception("object list required")
    if len(obj_list) == 1 and not obj_list[0]: raise Exception("object data required")
    obj_list = [dict(item) for item in obj_list]; [item.pop("id", None) for item in obj_list]
    if table == "spatial_ref_sys": raise Exception("system table protected")
    if mode == "buffer":
        result = "buffered"
        async for serialized_list in serialize_batches():
            key = f"{table}|{','.join(sorted(serialized_list[0].keys()))}"
            cache_postgres_buffer_create.setdefault(key, []).extend(serialized_list)
            if len(cache_postgres_buffer_create[key]) >= buffer_limit:
                items = cache_postgres_buffer_create[key]
                await insert_serialized(table, items)
                cache_postgres_buffer_create[key] = []
                result = "buffered released"
        return result
    if mode == "now":
        all_ids = []
        async def _execute_now(connection):
            async with connection.transaction():
                async for serialized_list in serialize_batches():
                    ids = await insert_serialized(table, serialized_list, connection=connection)
                    if isinstance(ids, list): all_ids.extend(ids)
            return all_ids if all_ids else "created"
        if client_postgres_conn:
            return await _execute_now(client_postgres_conn)
        async with client_postgres.acquire() as conn:
            return await _execute_now(conn)

async def func_postgres_read(*, client_postgres: any, client_password_hasher: any, func_postgres_serialize: callable, func_postgres_where_build: callable, func_postgres_relation: callable, cache_postgres_schema: dict, config_sql_read_limit_max: int, config_sql_read_relation_fetch_limit_max: int, table: str, filter: list, limit: int, page: int, order: str, column: str, relation: list) -> list:
    """Powerful generic PostgreSQL object reader with complex filtering, sorting, pagination, and relation fetching."""
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)): raise Exception(f"invalid identifier {table}")
    if limit < 1: raise Exception("query limit must be greater than 0")
    if page < 1: raise Exception("query page must be greater than 0")
    if config_sql_read_limit_max and limit > config_sql_read_limit_max: raise Exception(f"query limit {limit} exceeds maximum allowed: {config_sql_read_limit_max}")
    order = str(order or "").strip() or "id desc"
    order_list = []
    for part in order.split(","):
        p = part.strip().split()
        if p:
            # Allow alphanumeric, underscores, and spaces (for quoted identifiers)
            if not re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(p[0])): raise Exception(f"invalid identifier {p[0]}")
            col = p[0]
            direction = p[1].upper() if len(p) > 1 and p[1].lower() in ("asc", "desc") else "ASC"
            order_list.append(f'"{col}" {direction}')
    order_clause = ", ".join(order_list)
    column_list = "*"
    if column != "*":
        cols = []
        for c in column.split(","):
            c_strip = c.strip()
            if not re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(c_strip)): raise Exception(f"invalid identifier {c_strip}")
            cols.append(c_strip)
        column_list = ",".join([f'"{c}"' for c in cols])
    filters = filter
    where_statement, values = await func_postgres_where_build(client_postgres=client_postgres, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, table=table, filter=filters, prefix="")
    bind_idx = len(values) + 1
    sql_select = f'SELECT {column_list} FROM "{table}" {where_statement} ORDER BY {order_clause} LIMIT ${bind_idx} OFFSET ${bind_idx+1}'
    values.extend([limit, (page - 1) * limit])
    async with client_postgres.acquire() as conn:
        records = await conn.fetch(sql_select, *values)
        result_list = [dict(r) for r in records]
        if relation and result_list:
            result_list = await func_postgres_relation(client_postgres=client_postgres, client_postgres_conn=conn, obj_list=result_list, relation=relation, config_sql_read_relation_fetch_limit_max=config_sql_read_relation_fetch_limit_max)
        return result_list

async def func_postgres_update(*, client_postgres: any, client_postgres_conn: any, client_password_hasher: any, func_postgres_serialize: callable, func_regex_check: callable, cache_postgres_schema: dict, config_regex: dict, table: str, obj_list: list, created_by_id: int) -> any:
    """Update PostgreSQL records immediately with support for owner validation and dynamic serialization."""
    import re
    if not obj_list: raise Exception("object list required")
    if len(obj_list) == 1 and not obj_list[0]: raise Exception("object data required")
    if any(not isinstance(obj, dict) for obj in obj_list): raise Exception("object data invalid")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)): raise Exception(f"invalid identifier {table}")
    if table == "spatial_ref_sys": raise Exception("system table protected")
    if any("id" not in obj for obj in obj_list): raise Exception("missing required field: 'id' for update operation")
    update_cols = [c for c in obj_list[0] if c != "id" and (re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(c)) or (_ for _ in ()).throw(Exception(f"invalid identifier {c}")))]
    if not update_cols: raise Exception("update field required")
    if any(set(obj.keys()) != set(obj_list[0].keys()) for obj in obj_list): raise Exception("object keys mismatch")
    returned_ids = []
    limit_batch = 5000
    actual_batch_size = max(1, (limit_batch - (1 if created_by_id is not None else 0)) // ((2 * len(update_cols)) + 1))
    async def _execute_update(connection):
        async with connection.transaction():
            for i in range(0, len(obj_list), actual_batch_size):
                batch_raw = obj_list[i:i+actual_batch_size]
                await func_regex_check(config_regex=config_regex, obj_list=batch_raw)
                batch = await func_postgres_serialize(client_postgres=client_postgres, client_password_hasher=client_password_hasher, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=batch_raw, is_base=1)
                batch_vals, set_clauses = [], []
                for col in update_cols:
                    case_statements = []
                    for obj in batch:
                        batch_vals.extend([obj["id"], obj[col]])
                        case_statements.append(f'WHEN "id"=${len(batch_vals)-1}::bigint THEN ${len(batch_vals)}')
                    set_clauses.append(f'"{col}" = CASE {" ".join(case_statements)} ELSE "{col}" END')
                id_list = [obj["id"] for obj in batch]
                where_clause = f'"id" IN ({",".join(f"${len(batch_vals)+j+1}::bigint" for j in range(len(id_list)))})'
                if created_by_id is not None: where_clause += f' AND "created_by_id"=${len(batch_vals)+len(id_list)+1}'
                batch_vals.extend(id_list)
                if created_by_id is not None: batch_vals.append(created_by_id)
                sql = f'UPDATE "{table}" SET {", ".join(set_clauses)} WHERE {where_clause} RETURNING id;'
                returned_ids.extend([r["id"] for r in (await connection.fetch(sql, *batch_vals))])
    if client_postgres_conn: await _execute_update(client_postgres_conn)
    else:
        async with client_postgres.acquire() as conn: await _execute_update(conn)
    return returned_ids if returned_ids or len(obj_list) == 1 else "updated"

async def func_postgres_delete(*, client_postgres: any, client_postgres_conn: any, cache_postgres_schema: dict = None, table: str, ids: list, created_by_id: int) -> int:
    """Delete records by ID with schema-aware optional ownership restrictions."""
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)): raise Exception(f"invalid identifier {table}")
    if table == "spatial_ref_sys": raise Exception("system table protected")
    schema = (cache_postgres_schema or {}).get(table, {})
    if cache_postgres_schema is not None and table not in cache_postgres_schema: raise Exception(f"unknown table {table}")
    if schema and "id" not in schema: raise Exception(f"table {table} missing id column")
    if not ids or not isinstance(ids, (list, tuple)): raise Exception("ids required")
    id_list = [int(x) for x in ids]
    limit_chunk = 5000
    if created_by_id is not None:
        if schema and "created_by_id" not in schema: raise Exception(f"table {table} missing created_by_id column")
    async def _execute_delete(connection):
        deleted_count = 0
        async with connection.transaction():
            for i in range(0, len(id_list), limit_chunk):
                batch_ids = id_list[i:i+limit_chunk]
                where_clause = '"id" = ANY($1::bigint[])'
                values = [batch_ids]
                if created_by_id is not None:
                    where_clause += ' AND "created_by_id"=$2::bigint'
                    values.append(created_by_id)
                sql_delete = f'WITH deleted AS (DELETE FROM "{table}" WHERE {where_clause} RETURNING 1) SELECT COUNT(*) FROM deleted;'
                deleted_count += await connection.fetchval(sql_delete, *values)
        return deleted_count
    if client_postgres_conn:
        return await _execute_delete(client_postgres_conn)
    else:
        async with client_postgres.acquire() as conn:
            return await _execute_delete(conn)

async def func_producer(*, queue: str, client_celery_producer: any, client_kafka_producer: any, client_rabbitmq_producer: any, client_redis_producer: any, channel: str, payload: dict) -> any:
    """Ultra-standardized producer orchestration. Handles multi-tech dispatch with explicit clients."""
    import orjson
    allowed_queue_services = ["redis", "rabbitmq", "kafka", "celery"]
    if not queue: raise Exception("invalid queue format: queue missing")
    if queue not in allowed_queue_services: raise Exception(f"invalid queue: {queue}. allowed: {allowed_queue_services}")
    if queue == "celery":
        if not client_celery_producer: raise Exception("celery producer not initialized")
        return client_celery_producer.send_task(channel, kwargs=payload, queue=channel).id
    elif queue == "rabbitmq":
        import aio_pika
        if not client_rabbitmq_producer: raise Exception("rabbitmq producer not initialized")
        return await client_rabbitmq_producer.default_exchange.publish(aio_pika.Message(body=orjson.dumps(payload), delivery_mode=aio_pika.DeliveryMode.PERSISTENT), routing_key=channel)
    elif queue == "kafka":
        if not client_kafka_producer: raise Exception("kafka producer not initialized")
        return await client_kafka_producer.send_and_wait(channel, orjson.dumps(payload))
    elif queue == "redis":
        if not client_redis_producer: raise Exception("redis producer not initialized")
        return await client_redis_producer.lpush(channel, orjson.dumps(payload).decode("utf-8"))
    return None

async def func_otp_generate(*, client_postgres: any, email: str, mobile: str, config_otp_length: int) -> int:
    """Generate a random OTP and store it in PostgreSQL for a given email or mobile."""
    import random
    otp = random.randint(10**(config_otp_length-1), 10**config_otp_length - 1)
    sql = "INSERT INTO otp (otp, email, mobile) VALUES ($1, $2, $3);"
    async with client_postgres.acquire() as conn:
        await conn.execute(sql, otp, email.strip().lower() if email else None, mobile.strip() if mobile else None)
    return otp

async def func_otp_verify(*, client_postgres: any, otp: int, email: str, mobile: str, config_otp_expiry_sec: int) -> None:
    """Verify an OTP for email or mobile within its expiration window."""
    if not otp: raise Exception("otp code missing")
    if not email and not mobile: raise Exception("missing both email and mobile")
    if email and mobile: raise Exception("provide only one identifier")
    if email:
        sql = f"SELECT otp, (created_at > CURRENT_TIMESTAMP - INTERVAL '{config_otp_expiry_sec}s') as is_valid FROM otp WHERE email=$1 ORDER BY id DESC LIMIT 1"
        identifier = email.strip().lower()
    else:
        sql = f"SELECT otp, (created_at > CURRENT_TIMESTAMP - INTERVAL '{config_otp_expiry_sec}s') as is_valid FROM otp WHERE mobile=$1 ORDER BY id DESC LIMIT 1"
        identifier = mobile.strip()
    async with client_postgres.acquire() as conn:
        records = await conn.fetch(sql, identifier)
        if not records: raise Exception("otp not found")
        if records[0]["otp"] != otp: raise Exception("invalid otp code")
        if not records[0]["is_valid"]: raise Exception("otp code expired")
    return "done"

async def func_api_file_to_chunks(*, upload_file: any, chunk_size: int):
    """Generator: reads an uploaded CSV file in chunks and yields lists of dictionaries."""
    import csv, io
    is_wrapped_upload = hasattr(upload_file, "file")
    if is_wrapped_upload:
        await upload_file.seek(0)
        f = io.TextIOWrapper(upload_file.file, encoding="utf-8", newline="")
    else:
        content = await upload_file.read()
        f = io.StringIO(content.decode("utf-8"))
    chunk = []
    try:
        reader = csv.DictReader(f)
        for row in reader:
            chunk.append(row)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk: yield chunk
    finally:
        if is_wrapped_upload: f.detach()

async def func_user_read_single(*, client_postgres: any, user_id: int) -> dict:
    """Read a single user by ID from PostgreSQL, raises Exception if not found."""
    async with client_postgres.acquire() as conn:
        record = await conn.fetchrow("SELECT * FROM users WHERE id=$1;", user_id)
    if not record: raise Exception("user not found")
    return dict(record)

def func_run_broker(*, queue: str, channel: str, config_broker: dict, setup_callback: callable, execute_callback: callable):
    import sys, asyncio, orjson, os, traceback
    from datetime import datetime, timezone
    from itertools import count
    if not channel: raise Exception("channel name required")
    _run_counter = count(1)
    def log_failure(q, p, e):
        os.makedirs("tmp", exist_ok=True)
        try: payload_str = p.decode("utf-8") if isinstance(p, bytes) else p
        except Exception: payload_str = repr(p)
        record = {"time": datetime.now(timezone.utc).isoformat(), "queue": q, "channel": channel, "payload": payload_str, "error_type": type(e).__name__, "error": str(e), "traceback": traceback.format_exc()}
        with open("tmp/consumer_failed_payload.jsonl", "ab") as file: file.write(orjson.dumps(record, option=orjson.OPT_APPEND_NEWLINE))
    if queue == "celery":
        from celery import signals, Celery
        app = Celery("atom", broker=config_broker.get("config_celery_url"), backend=config_broker.get("config_celery_url"))
        app.conf.update(worker_prefetch_multiplier=1, task_acks_late=True, task_reject_on_worker_lost=True)
        setup_data, worker_loop = None, None
        @signals.worker_process_init.connect
        def init_worker(**kwargs):
            nonlocal worker_loop, setup_data
            worker_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(worker_loop)
            setup_data = worker_loop.run_until_complete(setup_callback())
        def run_async(*args, **kwargs):
            n = next(_run_counter)
            print(f"task started #{n}: {channel}", flush=True)
            nonlocal worker_loop, setup_data
            payload = kwargs.get("payload", {}) if "payload" in kwargs else kwargs
            if not worker_loop:
                worker_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(worker_loop)
                setup_data = worker_loop.run_until_complete(setup_callback())
            try:
                worker_loop.run_until_complete(execute_callback(payload, *setup_data))
                print(f"task completed #{n}: {channel}", flush=True)
                return None
            except Exception as e:
                log_failure("celery", payload, e)
                print(f"task failed #{n}: {channel} error: {str(e)}", flush=True)
                raise
        @app.task(name=channel)
        def celery_task(*args, **kwargs): return run_async(*args, **kwargs)
        app.worker_main(argv=["worker", "--loglevel=info", "-Q", channel, "-n", f"celery_{channel}@%h"])
        return
    async def async_runner():
        setup_data = await setup_callback()
        client_primary = setup_data[0]
        consumer_concurrency = 10
        semaphore = asyncio.Semaphore(consumer_concurrency)
        async def _execute(n, p):
            async with semaphore:
                try:
                    p_obj = orjson.loads(p)
                    await execute_callback(p_obj, *setup_data)
                    print(f"task completed #{n}: {channel}", flush=True)
                except Exception as e:
                    await asyncio.to_thread(log_failure, queue, p, e)
                    print(f"task failed #{n}: {channel} error: {str(e)}", flush=True)
        try:
            if queue == "redis":
                import redis.asyncio as redis
                client = redis.Redis.from_pool(redis.ConnectionPool.from_url(config_broker.get("config_redis_url_queue"))) if config_broker.get("config_redis_url_queue") else None
                print(f"redis consumer started on {channel}", flush=True)
                try:
                    while True:
                        msg = await client.brpop(channel, timeout=0)
                        if msg:
                            n = next(_run_counter)
                            print(f"task started #{n}: {channel}", flush=True)
                            asyncio.create_task(_execute(n, msg[1]))
                finally:
                    await client.aclose()
            elif queue == "rabbitmq":
                import aio_pika
                conn = await aio_pika.connect_robust(config_broker.get("config_rabbitmq_url"))
                ch = await conn.channel()
                await ch.set_qos(prefetch_count=consumer_concurrency)
                rq = await ch.declare_queue(channel, durable=True)
                print(f"rabbitmq consumer started on {channel}", flush=True)
                async def _execute_rmq(n, m):
                    async with m.process():
                        await _execute(n, m.body)
                try:
                    async with rq.iterator() as queue_iter:
                        async for msg in queue_iter:
                            n = next(_run_counter)
                            print(f"task started #{n}: {channel}", flush=True)
                            asyncio.create_task(_execute_rmq(n, msg))
                finally:
                    await conn.close()
            elif queue == "kafka":
                from aiokafka import AIOKafkaConsumer
                kafka_group_id = "atom"
                kafka_is_enable_auto_commit = 1
                kafka_batch_limit = 100
                kafka_batch_timeout_ms = 1000
                if config_broker.get("config_kafka_username"):
                    consumer = AIOKafkaConsumer(channel, bootstrap_servers=config_broker.get("config_kafka_url"), group_id=kafka_group_id, enable_auto_commit=bool(kafka_is_enable_auto_commit), security_protocol="SASL_SSL", sasl_mechanism="PLAIN", sasl_plain_username=config_broker.get("config_kafka_username"), sasl_plain_password=config_broker.get("config_kafka_password"))
                else:
                    consumer = AIOKafkaConsumer(channel, bootstrap_servers=config_broker.get("config_kafka_url"), group_id=kafka_group_id, enable_auto_commit=bool(kafka_is_enable_auto_commit))
                await consumer.start()
                print(f"kafka consumer started on {channel}", flush=True)
                try:
                    while True:
                        batch = await consumer.getmany(timeout_ms=kafka_batch_timeout_ms, max_records=kafka_batch_limit)
                        if not batch: continue
                        for tp, messages in batch.items():
                            tasks = []
                            for msg in messages:
                                n = next(_run_counter)
                                print(f"task started #{n}: {channel}", flush=True)
                                tasks.append(asyncio.create_task(_execute(n, msg.value)))
                            if tasks: await asyncio.gather(*tasks)
                            if not kafka_is_enable_auto_commit: await consumer.commit(tp)
                finally:
                    await consumer.stop()
            else:
                print(f"unknown queue: {queue}")
                sys.exit(1)
        finally:
            if client_primary: await client_primary.close()
    try: asyncio.run(async_runner())
    except KeyboardInterrupt: sys.exit(0)
    except Exception as e:
        print(f"critical error: {str(e)}")
        sys.exit(1)

def func_postgres_mark_read(*, client_postgres: any, table: str, ownership_column: str, user_id: int, ids: list) -> None:
    """Schedule a non-blocking read_at update for fetched objects owned by a user."""
    import asyncio, re
    if not ids: return
    for identifier in (table, ownership_column):
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(identifier)): raise Exception(f"invalid identifier {identifier}")
    read_ids = list(dict.fromkeys(int(obj_id) for obj_id in ids if obj_id is not None))
    if not read_ids: return
    async def update_read_at():
        async with client_postgres.acquire() as conn:
            await conn.execute(f'UPDATE "{table}" SET read_at=now() WHERE "{ownership_column}"=$1 AND "id"=ANY($2::bigint[]) AND read_at IS NULL', user_id, read_ids)
    task = asyncio.create_task(update_read_at())
    task.add_done_callback(lambda t: (t.exception() if not t.cancelled() else None))
    return None
