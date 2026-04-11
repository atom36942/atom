def func_app_read(lifespan_handler: any, is_debug_mode: int) -> any:
    """Initialize a FastAPI application with debug mode and lifespan handler, disabling default OpenAPI routes."""
    from fastapi import FastAPI
    return FastAPI(debug=bool(is_debug_mode), lifespan=lifespan_handler, openapi_url=None, docs_url=None, redoc_url=None)

def func_app_add_cors(fastapi_app: any, origins: list, methods: list, headers: list, is_allow_credentials: int) -> None:
    """Add CORS middleware to the FastAPI application."""
    from fastapi.middleware.cors import CORSMiddleware
    fastapi_app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=methods, allow_headers=headers, allow_credentials=bool(is_allow_credentials))

def func_app_add_prometheus(fastapi_app: any) -> None:
    """Expose Prometheus metrics for the FastAPI application."""
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(fastapi_app).expose(fastapi_app)

def func_app_state_add(fastapi_app: any, config_dict: dict, prefix: str) -> None:
    """Inject configuration values into the FastAPI application state based on a prefix."""
    for key, val in config_dict.items():
        if key.startswith(prefix):
            setattr(fastapi_app.state, key, val)

def func_app_add_sentry(sentry_dsn: str) -> None:
    """Initialize Sentry SDK for error tracking and profiling."""
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    sentry_sdk.init(dsn=sentry_dsn, integrations=[FastApiIntegration()], traces_sample_rate=1.0, profiles_sample_rate=1.0, send_default_pii=True)

def func_app_add_static(fastapi_app: any, folder_path: str, mount_path: str) -> None:
    """Mount a static directory to the FastAPI application."""
    from fastapi.staticfiles import StaticFiles
    fastapi_app.mount(mount_path, StaticFiles(directory=folder_path), name="static")

def func_app_add_router(fastapi_app: any) -> None:
    """Dynamically discover and include all FastAPI routers from the router directory."""
    import sys, importlib.util
    from pathlib import Path
    from fastapi import APIRouter
    root_dir = Path("./router").resolve()
    if not root_dir.exists():
        return None
    for py_file in root_dir.rglob("*.py"):
        if py_file.name.startswith((".", "__")):
            continue
        rel_path = py_file.relative_to(root_dir)
        module_name = "router." + ".".join(rel_path.with_suffix("").parts)
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            router = getattr(module, "router", None)
            if not isinstance(router, APIRouter):
                raise Exception(f"invalid router file: {py_file} (missing 'router' attribute of type APIRouter)")
            fastapi_app.include_router(router)

def func_openapi_spec_generate(app_routes: list, config_api_roles_auth: list = None, app_state: any = None) -> dict:
    """Generate a standard OpenAPI 3.0.0 specification from FastAPI routes using source inspection."""
    import inspect, re, ast
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "API Documentation", "version": "1.0.0"},
        "paths": {},
        "components": {"securitySchemes": {"BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}}
    }
    for route in app_routes:
        if not hasattr(route, "path"):
            continue
        if not hasattr(route, "endpoint"):
            continue
        path = route.path
        if path not in spec["paths"]:
            spec["paths"][path] = {}
        methods = list(getattr(route, "methods", []))
        if not methods and "WebSocket" in type(route).__name__:
            methods = ["WS"]
        for method in methods:
            m_lower = method.lower()
            path_parts = path.split("/")
            tag = path_parts[1] if len(path_parts) > 1 and path_parts[1] else "system"
            op = {"tags": [tag], "parameters": [], "responses": {"200": {"description": "Successful Response"}}}
            if any(path.startswith(x) for x in (config_api_roles_auth if config_api_roles_auth else [])):
                op["security"] = [{"BearerAuth": []}]
                op["parameters"].append({"name": "Authorization", "in": "header", "required": True, "schema": {"type": "string", "default": "Bearer {token}"}})
            for p in re.findall(r"\{(\w+)\}", path):
                op["parameters"].append({"name": p, "in": "path", "required": True, "schema": {"type": "string"}})
            try:
                sig = inspect.signature(route.endpoint)
                for name, par in sig.parameters.items():
                    p_type = par.annotation.__name__ if hasattr(par.annotation, "__name__") else str(par.annotation)
                    if name in ["request", "websocket", "req"]:
                        continue
                    if "Request" in p_type:
                        continue
                    if "Response" in p_type:
                        continue
                    if "WebSocket" in p_type:
                        continue
                    if "BackgroundTasks" in p_type:
                        continue
                    if any(x["name"] == name for x in op["parameters"]):
                        continue
                    param_def = {
                        "name": name,
                        "in": "query",
                        "required": par.default == inspect.Parameter.empty,
                        "schema": {
                            "type": "integer" if p_type == "int" else "string",
                            "default": None if par.default == inspect.Parameter.empty else par.default
                        }
                    }
                    op["parameters"].append(param_def)
                source = inspect.getsource(route.endpoint)
                tree = ast.parse(source)
                def eval_node(n):
                   if hasattr(ast, "Constant") and isinstance(n, ast.Constant):
                       return n.value
                   if hasattr(ast, "Str") and isinstance(n, ast.Str):
                       return n.s
                   if hasattr(ast, "Bytes") and isinstance(n, ast.Bytes):
                       return n.s
                   if hasattr(ast, "Num") and isinstance(n, ast.Num):
                       return n.n
                   if hasattr(ast, "NameConstant") and isinstance(n, ast.NameConstant):
                       return n.value
                   if isinstance(n, ast.List):
                       return [eval_node(e) for e in n.elts]
                   if isinstance(n, ast.Tuple):
                       return tuple(eval_node(e) for e in n.elts)
                   if hasattr(ast, "Attribute") and isinstance(n, ast.Attribute):
                       if hasattr(n.value, "id") and n.value.id == "st" and app_state:
                           return getattr(app_state, n.attr, None)
                   return None
                def ast_to_schema(n):
                    if isinstance(n, ast.Dict):
                        props = {}
                        for k, v in zip(n.keys, n.values):
                            k_name = eval_node(k)
                            if k_name:
                                props[k_name] = ast_to_schema(v)
                        return {"type": "object", "properties": props}
                    if isinstance(n, ast.List):
                        return {"type": "array", "items": ast_to_schema(n.elts[0]) if n.elts else {"type": "string"}}
                    if isinstance(n, ast.Tuple):
                        return {"type": "array", "items": ast_to_schema(n.elts[0]) if n.elts else {"type": "string"}}
                    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
                        s1 = ast_to_schema(n.left)
                        s2 = ast_to_schema(n.right)
                        p = {**(s1.get("properties", {})), **(s2.get("properties", {}))}
                        return {"type": "object", "properties": p}
                    if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "dict":
                         return {"type": "object"}
                    v = eval_node(n)
                    if isinstance(v, int):
                        return {"type": "integer", "default": v}
                    if isinstance(v, float):
                        return {"type": "number", "default": v}
                    if isinstance(v, bool):
                        return {"type": "boolean", "default": v}
                    if isinstance(v, list):
                        return {"type": "array", "items": {"type": "string"}}
                    if isinstance(v, dict):
                        return {"type": "object", "properties": {k: {"type": "string", "default": str(val)} for k, val in v.items()}}
                    return {"type": "string", "default": str(v) if v is not None else "str"}
                for node in ast.walk(tree):
                    if isinstance(node, ast.Return):
                        try:
                            op["responses"]["200"]["content"] = {"application/json": {"schema": ast_to_schema(node.value)}}
                        except Exception:
                            pass
                    if not isinstance(node, ast.Call):
                        continue
                    func_id = getattr(node.func, "id", None)
                    if not func_id:
                        func_id = getattr(node.func, "attr", None)
                    if func_id != "func_request_param_read":
                        continue
                    try:
                        p_loc = eval_node(node.args[1])
                        p_list = eval_node(node.args[2])
                        if p_list is not None and p_loc in ["header", "query"]:
                            for p in p_list:
                                if not p or not isinstance(p, (list, tuple)) or len(p) < 1:
                                    continue
                                op["parameters"] = [x for x in op["parameters"] if x["name"] != p[0]]
                                tp = "string"
                                fmt = None
                                itms = None
                                if len(p) > 1:
                                    dt = p[1]
                                    if dt in ["int", "bigint", "smallint", "integer", "int4", "int8"]:
                                        tp = "integer"
                                    elif dt in ["float", "number", "numeric"]:
                                        tp = "number"
                                    elif dt == "bool":
                                        tp = "boolean"
                                    elif dt in ["dict", "object"]:
                                        tp = "object"
                                    elif dt == "file":
                                        tp = "string"
                                        fmt = "binary"
                                    elif dt == "list" or dt.startswith("list:"):
                                        tp = "array"
                                        it_tp = "string"
                                        inner = dt.split(":")[1] if ":" in dt else "string"
                                        if inner in ["int", "bigint", "smallint", "integer", "int4", "int8"]:
                                            it_tp = "integer"
                                        elif inner in ["float", "number", "numeric"]:
                                            it_tp = "number"
                                        elif inner == "bool":
                                            it_tp = "boolean"
                                        elif inner in ["dict", "object"]:
                                            it_tp = "object"
                                        itms = {"type": it_tp}
                                op["parameters"].append({
                                    "name": p[0],
                                    "in": p_loc,
                                    "required": bool(p[2]) if len(p) > 2 else False,
                                    "schema": {
                                        "type": tp,
                                        "format": fmt,
                                        "items": itms,
                                        "pattern": p[5] if len(p) > 5 else None,
                                        "description": f"{p[6]}" if len(p) > 6 and p[6] else None
                                    }
                                })
                        elif p_list is not None and p_loc in ["body", "form"]:
                            media_type = "application/json" if p_loc == "body" else "multipart/form-data"
                            if "requestBody" not in op:
                                op["requestBody"] = {"content": {media_type: {"schema": {"type": "object"}}}}
                            if p_list:
                                schema_obj = op["requestBody"]["content"][media_type]["schema"]
                                if "properties" not in schema_obj:
                                    schema_obj["properties"] = {}
                                if "required" not in schema_obj:
                                    schema_obj["required"] = []
                                props = schema_obj["properties"]
                                for p in p_list:
                                    if not p or not isinstance(p, (list, tuple)) or len(p) < 1:
                                        continue
                                    tp = "string"
                                    fmt = None
                                    itms = None
                                    if len(p) > 1:
                                        dt = p[1]
                                        if dt in ["int", "bigint", "smallint", "integer", "int4", "int8"]:
                                            tp = "integer"
                                        elif dt in ["float", "number", "numeric"]:
                                            tp = "number"
                                        elif dt == "bool":
                                            tp = "boolean"
                                        elif dt in ["dict", "object"]:
                                            tp = "object"
                                        elif dt == "file":
                                            tp = "string"
                                            fmt = "binary"
                                        elif dt == "list" or dt.startswith("list:"):
                                            tp = "array"
                                            it_tp = "string"
                                            inner = dt.split(":")[1] if ":" in dt else "string"
                                            if inner in ["int", "bigint", "smallint", "integer", "int4", "int8"]:
                                                it_tp = "integer"
                                            elif inner in ["float", "number", "numeric"]:
                                                it_tp = "number"
                                            elif inner == "bool":
                                                it_tp = "boolean"
                                            elif inner in ["dict", "object"]:
                                                it_tp = "object"
                                            itms = {"type": it_tp}
                                    props[p[0]] = {
                                        "type": tp,
                                        "format": fmt,
                                        "items": itms,
                                        "enum": p[3] if len(p) > 3 and isinstance(p[3], (list, tuple)) else None,
                                        "default": p[4] if len(p) > 4 else None,
                                        "pattern": p[5] if len(p) > 5 else None,
                                        "description": f"{p[6]}" if len(p) > 6 and p[6] else None
                                    }
                                    if len(p) > 2 and bool(p[2]):
                                        schema_obj["required"].append(p[0])
                    except Exception:
                        pass
            except Exception:
                pass

            spec["paths"][path][m_lower] = op
    return spec

def func_check(app_routes: list, current_config_api: dict, allowed_roles: list = None, config_postgres: dict = None, api_roles_auth: list = None) -> None:
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

def func_repo_info(app_routes: list, cache_postgres_schema: dict, config_postgres: dict, config_table: dict, config_api: dict) -> dict:
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
                        if len(node.args) > 2 and isinstance(node.args[2], ast.List):
                            for elt in node.args[2].elts:
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
