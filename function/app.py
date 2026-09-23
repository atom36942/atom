"""Atom app functions."""

async def func_admin_sync(*, app_state: any, app_routes: list = None) -> str:
    """Synchronize and refresh all application state caches, schemas, OpenAPI spec, and config maps."""
    if getattr(app_state, "client_postgres", None):
        await app_state.func_postgres_create(client_postgres=app_state.client_postgres, client_postgres_conn=None, client_password_hasher=None, func_postgres_serialize=None, cache_postgres_schema=app_state.cache_postgres_schema, mode="flush", table=None, obj_list=None, buffer_limit=None, cache_postgres_buffer=app_state.cache_postgres_buffer_create, config_column_regex=None, func_regex_check=None)
    app_state.cache_postgres_schema = await app_state.func_postgres_schema_read(client_postgres=app_state.client_postgres) if getattr(app_state, "client_postgres", None) else {}
    app_state.cache_postgres_schema_ai = await app_state.func_postgres_schema_read_ai(client_postgres=app_state.client_postgres) if getattr(app_state, "client_postgres", None) else {}
    app_state.cache_clickhouse_schema_ai = await app_state.func_clickhouse_schema_read_ai(client_clickhouse=app_state.client_clickhouse) if getattr(app_state, "client_clickhouse", None) else {}
    app_state.cache_postgres_schema_dict = {name: await app_state.func_postgres_schema_read(client_postgres=client) for name, client in getattr(app_state, "client_postgres_dict", {}).items()}
    app_state.cache_postgres_schema_ai_dict = {name: await app_state.func_postgres_schema_read_ai(client_postgres=client) for name, client in getattr(app_state, "client_postgres_dict", {}).items()}
    if app_routes is not None:
        app_state.cache_openapi = app_state.func_openapi_spec_generate(app_routes=app_routes, app_state=app_state)
    app_state.cache_config = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres, config_sql=app_state.config_sql.get("config"), is_json_value=True) if getattr(app_state, "client_postgres", None) and "config" in app_state.cache_postgres_schema else {}
    app_state.cache_users_role = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres, config_sql=app_state.config_sql.get("users_role")) if getattr(app_state, "client_postgres", None) else {}
    app_state.cache_users_deactivated = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres, config_sql=app_state.config_sql.get("users_deactivated")) if getattr(app_state, "client_postgres", None) else {}
    app_state.cache_users_deleted = await app_state.func_postgres_map_column(client_postgres=app_state.client_postgres, config_sql=app_state.config_sql.get("users_deleted")) if getattr(app_state, "client_postgres", None) else {}
    if hasattr(app_state, "cache_extend") and isinstance(app_state.cache_extend, dict): app_state.cache_extend.clear()
    return "done"

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

def func_app_static_add(*, app: any, path: str = "/static", directory: str = "./static") -> None:
    """Mount static directory on FastAPI application."""
    from fastapi.staticfiles import StaticFiles
    app.mount(path, StaticFiles(directory=directory, check_dir=False), name="static")

def func_app_cors_add(*, app: any, allow_origins: list = None, allow_origin_regex: str = None, allow_methods: list = None, allow_headers: list = None, expose_headers: list = None, allow_credentials: bool = True) -> None:
    """Configure CORS middleware on FastAPI application if origins are provided."""
    if not allow_origins and not allow_origin_regex: return
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(CORSMiddleware, allow_origins=allow_origins or [], allow_origin_regex=allow_origin_regex, allow_methods=allow_methods or ["*"], allow_headers=allow_headers or ["*"], expose_headers=expose_headers or ["*"], allow_credentials=allow_credentials)

def func_app_fastapi_create(*, config_is_prod: bool = True, lifespan: any = None):
    """Create and configure the primary FastAPI application instance."""
    from fastapi import FastAPI
    return FastAPI(debug=not config_is_prod, lifespan=lifespan, openapi_url=None, docs_url=None, redoc_url=None)

def func_app_state_add(*, app: any, data_dict: dict, prefixes: tuple) -> None:
    """Bulk register objects matching specific key prefixes onto app.state."""
    for k, v in data_dict.items():
        if k.startswith(prefixes):
            setattr(app.state, k, v)

def func_sentry_init(*, config_sentry_dsn: str):
    """Initialize Sentry SDK monitoring if DSN is configured."""
    if not config_sentry_dsn: return None
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    return sentry_sdk.init(dsn=config_sentry_dsn, integrations=[FastApiIntegration()], traces_sample_rate=1.0, profiles_sample_rate=1.0, send_default_pii=False)

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
            is_token_required = api_cfg.get("is_token", False) or "user_check_role" in api_cfg
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
                    if func_id == "func_extract_request_object_list":
                        body = op.setdefault("requestBody", {})
                        body["required"] = True
                        body["description"] = "A single record object, or an object with an obj_list array for batch operations. Record fields depend on the selected table."
                        content = body.setdefault("content", {})
                        json_body = content.setdefault("application/json", {})
                        schema = json_body.setdefault("schema", {"type": "object", "properties": {}, "required": []})
                        schema["additionalProperties"] = True
                        continue
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
                                reg_info = getattr(app_state, "config_column_regex", {}).get(p_name) if is_regex_enabled else None
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
                                reg_info = getattr(app_state, "config_column_regex", {}).get(p_name) if is_regex_enabled else None
                                dt = p.get("type", "str")
                                props[p_name] = {"type": TYPE_MAP.get(dt.split(":")[0], "string"), "format": "binary" if dt == "file" else None, **({"items": {"type": TYPE_MAP.get(dt.split(":")[1], "string")}} if ":" in dt else {}), "enum": p.get("allowed") if isinstance(p.get("allowed"), (list, tuple)) else None, "default": p.get("default"), "pattern": reg_info[0] if reg_info and len(reg_info) > 0 else None, "description": reg_info[1] if reg_info and len(reg_info) > 1 else None}
                                if bool(p.get("required", False)): reqs.append(p_name)
                    except: pass
            except: pass
            spec["paths"][path][m_lower] = op
    return spec
