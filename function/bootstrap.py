def func_check(*, app_routes: list, current_config_api: dict, allowed_roles: list, config_postgres: dict, api_roles_auth: list) -> None:
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
    def get_control_errors(config_pg):
        if not config_pg:
            return []
        if "control" not in config_pg:
            return []
        errs = []
        ctrl = config_pg["control"]
        for k, v in ctrl.items():
            if k.startswith("is_") and v not in (None, 0, 1):
                errs.append(f"invalid value for {k}: {v} (allowed: 0, 1, None)")
        tdd = ctrl.get("table_row_delete_disable")
        if not isinstance(tdd, list):
            errs.append("table_row_delete_disable must be a list")
        elif "*" in tdd and len(tdd) > 1:
            errs.append("exclusive wildcard violation: table_row_delete_disable cannot contain other tables if '*' is present")
        tddb = ctrl.get("table_row_delete_disable_bulk")
        if not isinstance(tddb, list):
            errs.append("table_row_delete_disable_bulk must be a list")
        else:
            is_star = any(isinstance(x, (list, tuple)) and x and x[0] == "*" for x in tddb)
            if is_star and len(tddb) > 1:
                errs.append("exclusive wildcard violation: table_row_delete_disable_bulk cannot contain other tables if '*' is present")
            for x in tddb:
                if not isinstance(x, (list, tuple)):
                    errs.append(f"invalid bulk delete format: {x} (expected array)")
                    continue
                if len(x) < 2:
                    errs.append(f"invalid bulk delete format: {x} (expected [table, limit])")
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
    def get_table_integrity_errors(config_pg):
        from core import config
        if not config_pg:
            return []
        if "table" not in config_pg:
            return []
        errs = []
        db_tables = set(config_pg["table"].keys())
        for k in ("config_table_create_my", "config_table_create_public", "config_table_read_public", "config_table"):
            v = getattr(config, k, [] if k != "config_table" else {})
            v_list = v.keys() if k == "config_table" else v
            for table in v_list:
                if table not in db_tables:
                    errs.append(f"table reference integrity violation: {table} (referenced in {k}) does not exist in config_postgres")
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
    if api_roles_auth is not None and not isinstance(api_roles_auth, (list, tuple)):
        raise Exception("config_api_roles_auth must be a list")
    errors = get_duplicate_errors("config.py", "config_api") + get_route_errors(app_paths, current_config_api) + get_admin_errors(app_routes, current_config_api) + get_mode_errors(current_config_api) + get_api_role_errors(app_routes, allowed_roles) + get_switch_errors() + get_control_errors(config_postgres) + get_cors_errors() + get_table_integrity_errors(config_postgres) + get_api_id_errors(current_config_api) + get_enum_type_errors()
    if errors:
        raise Exception("; ".join(errors))

def func_repo_info(*, app_routes: list, cache_postgres_schema: dict, config_postgres: dict, config_table: dict, config_api: dict) -> dict:
    """Construct system discovery metadata including routes, schema, and configuration settings."""
    import inspect, ast
    def get_postgres_keys(config_pg):
        postgres_key = {}
        for k, v in config_pg.items():
            if k == "table":
                table_keys = set()
                for cv in v.values():
                    for item in cv:
                        for ck in item:
                            table_keys.add(ck)
                postgres_key[k] = sorted(list(table_keys))
            elif isinstance(v, dict):
                postgres_key[k] = sorted(list(v.keys()))
            else:
                postgres_key[k] = []
        return postgres_key
    def get_api_param_count(routes):
        param_counts = {}
        for route in routes:
            if not hasattr(route, "endpoint"):
                continue
            try:
                for node in ast.walk(ast.parse(inspect.getsource(route.endpoint))):
                    if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", None)) == "func_request_param_read":
                        p_list_node = None
                        for kw in node.keywords:
                            if kw.arg == "config": p_list_node = kw.value
                        if p_list_node is None and len(node.args) > 2: p_list_node = node.args[2]
                        if isinstance(p_list_node, ast.List):
                            for elt in p_list_node.elts:
                                if isinstance(elt, (ast.Tuple, ast.List)) and len(elt.elts) > 0:
                                    val = getattr(elt.elts[0], "value", getattr(elt.elts[0], "s", None))
                                    if isinstance(val, str):
                                        param_counts[val] = param_counts.get(val, 0) + 1
            except Exception:
                pass
        return dict(sorted(param_counts.items(), key=lambda x: x[1], reverse=True))
    def get_config_keys(cfg):
        return sorted(list(set(k for v in cfg.values() for k in v)))
    return {
        "api_list": [route.path for route in app_routes if hasattr(route, "path")],
        "api_param_count": get_api_param_count(app_routes),
        "postgres_schema": cache_postgres_schema,
        "config_table_key": get_config_keys(config_table),
        "config_api_key": get_config_keys(config_api),
        "config_postgres_key": get_postgres_keys(config_postgres)
    }
