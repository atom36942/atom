def func_check(*, app_routes: list, current_config_api: dict, allowed_roles: list, api_roles_auth: list) -> None:
    """Validate config_api consistency with app routes, admin roles, valid modes, duplicate keys, and strict api roles."""
    import ast
    def get_duplicate_errors(file_path, var_name):
        try:
            with open(file_path, "r") as f:
                tree = ast.parse(f.read())
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == var_name:
                            if isinstance(node.value, ast.Dict):
                                keys = []
                                for k in node.value.keys:
                                    if isinstance(k, ast.Constant):
                                        keys.append(k.value)
                                    elif isinstance(k, ast.Str):
                                        keys.append(k.s)
                                duplicates = [str(k) for k in set(keys) if keys.count(k) > 1]
                                return [f"duplicate keys in {var_name}: {', '.join(duplicates)}"] if duplicates else []
        except Exception:
            pass
        return []
    app_paths = {route.path for route in app_routes if hasattr(route, "path")}
    def get_route_errors(paths, config):
        missing = [p for p in config if p not in paths]
        return [f"""config_api paths missing from app: {", ".join(missing)}"""] if missing else []
    def get_admin_errors(routes, config):
        errs = []
        for route in routes:
            if hasattr(route, "path") and route.path.startswith("/admin/"):
                if route.path not in config:
                    errs.append(f"{route.path} missing from config_api")
                else:
                    roles_cfg = config[route.path].get("user_role_check", [])
                    allowed_roles_cfg = roles_cfg[1] if roles_cfg and isinstance(roles_cfg[0], str) else roles_cfg
                    if 1 not in (allowed_roles_cfg if isinstance(allowed_roles_cfg, (list, tuple, set)) else []):
                        errs.append(f"{route.path} missing role 1")
        return errs
    def get_mode_errors(config):
        errs = []
        rules = {"user_role_check": ["redis", "realtime", "inmemory", "token"], "user_is_active_check": ["redis", "realtime", "inmemory", "token"], "api_cache_sec": ["redis", "inmemory"], "api_ratelimiting_times_sec": ["redis", "inmemory"]}
        for path, cfg in config.items():
            for key, allowed in rules.items():
                if key in cfg:
                    setting = cfg[key]
                    if not isinstance(setting, (list, tuple)) or len(setting) < 2 or setting[0] not in allowed:
                        errs.append(f"{path} invalid {key} mode (allowed: {allowed})")
        return errs
    def get_api_role_errors(routes, allowed):
        if not allowed:
            return []
        errs = []
        for route in routes:
            if hasattr(route, "path"):
                role = route.path.split("/")[1] if len(route.path.split("/")) > 2 else "index"
                if role not in allowed:
                    errs.append(f"invalid api role in path {route.path}: {role}")
        return errs
    def get_cors_errors():
        from core import config
        errs = []
        for k in ("config_cors_origin", "config_cors_method", "config_cors_headers"):
            v = getattr(config, k, None)
            if not isinstance(v, list):
                errs.append(f"{k} must be a list")
            elif "*" in v and len(v) > 1:
                errs.append(f"exclusive wildcard violation: {k} cannot contain other values if '*' is present")
        return errs
    def get_switch_errors():
        from core import config
        errs = []
        for key, value in vars(config).items():
            if key.startswith("config_is_"):
                if value not in (None, 0, 1):
                    errs.append(f"invalid value for {key}: {value} (allowed: 0, 1, None)")
        return errs
    def get_api_id_errors(config_api):
        missing = [p for p, v in config_api.items() if not isinstance(v, dict) or "id" not in v]
        if missing:
            return [f"missing mandatory API ID for: {', '.join(missing)}"]
        ids = [v["id"] for v in config_api.values()]
        dupes = [str(i) for i in set(ids) if ids.count(i) > 1]
        return [f"duplicate API IDs in config_api: {', '.join(dupes)}"] if dupes else []
    def get_enum_type_errors():
        from core import config
        errs = []
        checks = {"config_auth_type": int, "config_token_key": str, "config_api_roles": str}
        for k, t in checks.items():
            v = getattr(config, k, None)
            if not isinstance(v, list):
                errs.append(f"{k} must be a list")
            elif not all(isinstance(x, t) for x in v):
                errs.append(f"{k} must be a list of {t.__name__}s")
        return errs
    def get_schema_errors():
        from core import config
        errs = []
        tables = config.config_postgres.get("table", {})
        for table_name, columns in tables.items():
            if not columns:
                errs.append(f"table {table_name} has no columns defined")
            else:
                col_names = [c.get("name") for c in columns if isinstance(c, dict)]
                dupes = [n for n in set(col_names) if col_names.count(n) > 1]
                if dupes:
                    errs.append(f"duplicate columns in {table_name}: {', '.join(dupes)}")
        return errs
    def get_mapping_errors():
        from core import config
        errs = []
        all_cols = set()
        for columns in config.config_postgres.get("table", {}).values():
            all_cols.update(c.get("name") for c in columns if isinstance(c, dict) and "name" in c)
        for k in ("config_column_blocked", "config_column_single_update"):
            v = getattr(config, k, [])
            missing = [c for c in v if c not in all_cols]
            if missing:
                errs.append(f"columns in {k} missing from schema: {', '.join(missing)}")
        return errs
    def get_retention_errors():
        from core import config
        errs = []
        for table_name, cfg in config.config_table.items():
            retention = cfg.get("retention_day")
            if retention is not None and (not isinstance(retention, int) or retention <= 0):
                errs.append(f"invalid retention_day for {table_name}: {retention} (must be positive integer)")
        return errs
    if api_roles_auth is not None and not isinstance(api_roles_auth, (list, tuple)):
        raise Exception("config_api_roles_auth must be a list")
    errors = get_duplicate_errors("config.py", "config_api") + get_route_errors(app_paths, current_config_api) + get_admin_errors(app_routes, current_config_api) + get_mode_errors(current_config_api) + get_api_role_errors(app_routes, allowed_roles) + get_switch_errors() + get_cors_errors() + get_api_id_errors(current_config_api) + get_enum_type_errors() + get_schema_errors() + get_mapping_errors() + get_retention_errors()
    if errors:
        raise Exception("; ".join(errors))
    return None
async def func_check_ratelimiter(*, client_redis_ratelimiter: any, config_api: dict, url_path: str, identifier: str, cache_ratelimiter: dict) -> None:
    """Check and enforce API rate limits using either Redis or in-memory storage."""
    import time
    api_cfg = config_api.get(url_path, {})
    rl_config = api_cfg.get("api_ratelimiting_times_sec")
    if not rl_config:
        return None
    mode, limit, window = rl_config
    cache_key = f"ratelimiter:{url_path}:{identifier}"
    if mode == "redis":
        if not client_redis_ratelimiter:
            raise Exception("redis client missing")
        current_count = await client_redis_ratelimiter.get(cache_key)
        if current_count and int(current_count) + 1 > limit:
            raise Exception("ratelimiter exceeded")
        pipeline = client_redis_ratelimiter.pipeline()
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
