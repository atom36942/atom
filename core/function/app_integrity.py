def func_structure_create(*, directories: list, files: list) -> None:
    """Ensure required directory structure and files exist on startup."""
    import os
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
    for file in files:
        if not os.path.exists(file):
            with open(file, "w") as f:
                pass
    return None
    
async def func_check(*, app_routes: list, current_config_api: dict, allowed_roles: list, api_roles_auth: list, client_postgres_pool: any = None) -> None:
    """Orchestrate all application consistency checks (routes, roles, modes, and database indexes)."""
    import ast
    def _get_duplicate_errors(file_path, var_name):
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
    def _get_route_errors(app_paths, config):
        missing = [p for p in config if p not in app_paths]
        return [f"""config_api paths missing from app: {", ".join(missing)}"""] if missing else []
    def _get_admin_errors(app_routes, config):
        errs = []
        for route in app_routes:
            if hasattr(route, "path") and route.path.startswith("/admin/"):
                if route.path not in config:
                    errs.append(f"{route.path} missing from config_api")
                else:
                    roles_cfg = config[route.path].get("user_role_check", [])
                    allowed_roles_cfg = roles_cfg[1] if roles_cfg and isinstance(roles_cfg[0], str) else roles_cfg
                    if 1 not in (allowed_roles_cfg if isinstance(allowed_roles_cfg, (list, tuple, set)) else []):
                        errs.append(f"{route.path} missing role 1")
        return errs
    def _get_mode_errors(config):
        errs = []
        rules = {"user_role_check": ["redis", "realtime", "inmemory", "token"], "user_is_active_check": ["redis", "realtime", "inmemory", "token"], "api_cache_sec": ["redis", "inmemory"], "api_ratelimiting_times_sec": ["redis", "inmemory"]}
        for path, cfg in config.items():
            for key, allowed in rules.items():
                if key in cfg:
                    setting = cfg[key]
                    if not isinstance(setting, (list, tuple)) or len(setting) < 2 or setting[0] not in allowed:
                        errs.append(f"{path} invalid {key} mode (allowed: {allowed})")
        return errs
    def _get_api_role_errors(app_routes, allowed):
        if not allowed:
            return []
        errs = []
        for route in app_routes:
            if hasattr(route, "path"):
                role = route.path.split("/")[1] if len(route.path.split("/")) > 2 else "index"
                if role not in allowed:
                    errs.append(f"invalid api role in path {route.path}: {role}")
        return errs
    def _get_cors_errors():
        from core import config
        errs = []
        for k in ("config_cors_origin", "config_cors_method", "config_cors_headers"):
            v = getattr(config, k, None)
            if not isinstance(v, list):
                errs.append(f"{k} must be a list")
            elif "*" in v and len(v) > 1:
                errs.append(f"exclusive wildcard violation: {k} cannot contain other values if '*' is present")
        return errs
    def _get_switch_errors():
        from core import config
        errs = []
        for key, value in vars(config).items():
            if key.startswith("config_is_"):
                if value not in (None, 0, 1):
                    errs.append(f"invalid value for {key}: {value} (allowed: 0, 1, None)")
        return errs
    def _get_api_id_errors(config_api):
        missing = [p for p, v in config_api.items() if not isinstance(v, dict) or "id" not in v]
        if missing:
            return [f"missing mandatory API ID for: {', '.join(missing)}"]
        ids = [v["id"] for v in config_api.values()]
        dupes = [str(i) for i in set(ids) if ids.count(i) > 1]
        return [f"duplicate API IDs in config_api: {', '.join(dupes)}"] if dupes else []
    def _get_schema_errors():
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
    async def _get_index_errors(pool):
        if not pool:
            return []
        query = """
            SELECT 
                t.relname AS table_name,
                a.attname AS column_name,
                am.amname AS index_type,
                COUNT(ix.indexrelid) AS index_count
            FROM pg_class t
            JOIN pg_attribute a ON a.attrelid = t.oid
            JOIN pg_index ix ON t.oid = ix.indrelid AND a.attnum = ix.indkey[0]
            JOIN pg_class i ON ix.indexrelid = i.oid
            JOIN pg_am am ON i.relam = am.oid
            WHERE t.relkind = 'r' 
              AND t.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
              AND ix.indisunique = false  -- Only flag non-unique indexes as redundant
            GROUP BY t.relname, a.attname, am.amname
            HAVING COUNT(ix.indexrelid) > 1;
        """
        records = await pool.fetch(query)
        return [f"table '{r['table_name']}' has redundant non-unique {r['index_type']} indexes starting with column '{r['column_name']}' ({r['index_count']} indexes found)" for r in records]
    if api_roles_auth is not None and not isinstance(api_roles_auth, (list, tuple)):
        raise Exception("config_api_roles_auth must be a list")
    app_paths = {route.path for route in app_routes if hasattr(route, "path")}
    async def _get_root_user_errors(pool):
        if not pool:
            return []
        res = await pool.fetchval("SELECT COUNT(*) FROM users WHERE id = 1")
        return ["root user (id=1) missing from users table"] if not res else []
    def _get_function_standard_errors():
        import os
        errs = []
        folder = "core/function"
        for filename in os.listdir(folder):
            if filename.endswith(".py") and filename != "__init__.py":
                path = os.path.join(folder, filename)
                try:
                    with open(path, "r") as f:
                        tree = ast.parse(f.read())
                    for node in tree.body:
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            # 1. Prefix Check
                            if not node.name.startswith("func_"):
                                errs.append(f"function '{node.name}' in {filename} must start with 'func_'")
                                continue
                            
                            # 2. Docstring Check
                            if not ast.get_docstring(node):
                                errs.append(f"function '{node.name}' in {filename} is missing a docstring")
                            
                            # 3. Keyword-Only Check
                            if node.args.args:
                                errs.append(f"function '{node.name}' in {filename} must use keyword-only arguments (use '*' in signature)")
                            
                            # 4. Type Hint Check
                            for arg in node.args.kwonlyargs:
                                if not arg.annotation:
                                    errs.append(f"parameter '{arg.arg}' in function '{node.name}' ({filename}) is missing a type hint")
                except Exception:
                    pass
        return errs
    def _get_import_errors():
        import os
        errs = []
        folder = "core/function"
        hierarchy_violations = ["core.router", "main"]
        for filename in os.listdir(folder):
            if filename.endswith(".py") and filename != "__init__.py":
                path = os.path.join(folder, filename)
                try:
                    with open(path, "r") as f:
                        tree = ast.parse(f.read())
                    for node in tree.body:
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            errs.append(f"global import found in {filename}: {ast.dump(node)}")
                        
                        # Hierarchy Check (search all imports in the tree)
                        for subnode in ast.walk(tree):
                            if isinstance(subnode, ast.Import):
                                for alias in subnode.names:
                                    if any(alias.name.startswith(v) for v in hierarchy_violations):
                                        errs.append(f"hierarchy violation: {filename} imports from forbidden module '{alias.name}'")
                            elif isinstance(subnode, ast.ImportFrom):
                                if subnode.module and any(subnode.module.startswith(v) for v in hierarchy_violations):
                                    errs.append(f"hierarchy violation: {filename} imports from forbidden module '{subnode.module}'")
                except Exception:
                    pass
        return errs
    def _get_config_standard_errors():
        errs = []
        path = "core/config.py"
        try:
            with open(path, "r") as f:
                tree = ast.parse(f.read())
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and not target.id.startswith("config_"):
                            errs.append(f"variable '{target.id}' in config.py must start with 'config_'")
        except Exception:
            pass
        return errs
    errors = (
        _get_duplicate_errors("config.py", "config_api") +
        _get_route_errors(app_paths, current_config_api) +
        _get_admin_errors(app_routes, current_config_api) +
        _get_mode_errors(current_config_api) +
        _get_api_role_errors(app_routes, allowed_roles) +
        _get_switch_errors() +
        _get_cors_errors() +
        _get_api_id_errors(current_config_api) +
        _get_schema_errors() +
        (await _get_index_errors(client_postgres_pool)) +
        (await _get_root_user_errors(client_postgres_pool)) +
        _get_config_standard_errors() +
        _get_function_standard_errors() +
        _get_import_errors()
    )
    if errors:
        raise Exception("; ".join(errors))
    return None

def func_openapi_spec_generate(*, app_routes: list, config_api_roles_auth: list, app_state: any) -> dict:
    """Generate a standard OpenAPI 3.0.0 specification from FastAPI routes using source inspection."""
    import inspect, re, ast
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
        if isinstance(n, ast.Attribute) and hasattr(n.value, "id") and n.value.id == "app_state" and app_state: return getattr(app_state, n.attr, None)
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
            if any(path.startswith(x) for x in config_api_roles_auth):
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
                    hardened_funcs = ("func_regex_check", "func_orchestrator_obj_create", "func_orchestrator_obj_update", "func_orchestrator_postgres_import")
                    is_regex_enabled = any(isinstance(n, ast.Call) and (getattr(n.func, "id", None) in hardened_funcs or getattr(n.func, "attr", None) in hardened_funcs) for n in ast.walk(tree))
                    try:
                        p_loc, p_list = None, None
                        for kw in node.keywords:
                            if kw.arg == "mode": p_loc = eval_node(kw.value)
                            elif kw.arg == "config": p_list = eval_node(kw.value)
                        if p_loc is None and len(node.args) > 1: p_loc = eval_node(node.args[1])
                        if p_list is None and len(node.args) > 2: p_list = eval_node(node.args[2])
                        if p_list is not None and p_loc in ["header", "query"]:
                            for p in p_list:
                                if not p or not isinstance(p, (list, tuple)) or len(p) < 1: continue
                                op["parameters"] = [x for x in op["parameters"] if x["name"] != p[0]]
                                dt = p[1] if len(p) > 1 else "str"
                                tp = TYPE_MAP.get(dt.split(":")[0], "string")
                                itms = {"type": TYPE_MAP.get(dt.split(":")[1], "string")} if ":" in dt else None
                                reg_info = getattr(app_state, "config_regex", {}).get(p[0]) if is_regex_enabled else None
                                op["parameters"].append({
                                    "name": p[0], "in": p_loc, "required": bool(p[2]) if len(p) > 2 else False,
                                    "description": reg_info[1] if reg_info and len(reg_info) > 1 else None,
                                    "schema": {"type": tp, "format": "binary" if dt == "file" else None, **({"items": itms} if itms else {}), "enum": p[3] if len(p) > 3 and isinstance(p[3], (list, tuple)) else None, "default": p[4] if len(p) > 4 else None, "pattern": reg_info[0] if reg_info and len(reg_info) > 0 else None}
                                })
                        elif p_list is not None and p_loc in ["body", "form"]:
                            media_type = "application/json" if p_loc == "body" else "multipart/form-data"
                            if "requestBody" not in op: op["requestBody"] = {"content": {media_type: {"schema": {"type": "object", "properties": {}, "required": []}}}}
                            props, reqs = op["requestBody"]["content"][media_type]["schema"]["properties"], op["requestBody"]["content"][media_type]["schema"]["required"]
                            for p in p_list:
                                if not p or not isinstance(p, (list, tuple)) or len(p) < 1: continue
                                reg_info = getattr(app_state, "config_regex", {}).get(p[0]) if is_regex_enabled else None
                                dt = p[1] if len(p) > 1 else "str"
                                props[p[0]] = {"type": TYPE_MAP.get(dt.split(":")[0], "string"), "format": "binary" if dt == "file" else None, **({"items": {"type": TYPE_MAP.get(dt.split(":")[1], "string")}} if ":" in dt else {}), "enum": p[3] if len(p) > 3 and isinstance(p[3], (list, tuple)) else None, "default": p[4] if len(p) > 4 else None, "pattern": reg_info[0] if reg_info and len(reg_info) > 0 else None, "description": reg_info[1] if reg_info and len(reg_info) > 1 else None}
                                if len(p) > 2 and bool(p[2]): reqs.append(p[0])
                    except: pass
            except: pass
            spec["paths"][path][m_lower] = op
    return spec

def func_config_override_from_env(*, global_dict: dict) -> None:
    """Override configuration variables starting with 'config_' from environment variables and .env file."""
    import orjson, os, ast
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")
    for key, value in list(global_dict.items()):
        val_env = os.getenv(key)
        if key.startswith("config_") and val_env is not None:
            config_val = val_env
            if isinstance(global_dict[key], (list, tuple)):
                global_dict[key] = orjson.loads(config_val)
            elif isinstance(value, bool):
                global_dict[key] = 1 if config_val.lower() in ("true", "1", "yes", "on", "ok") else 0
            elif isinstance(value, int):
                global_dict[key] = int(config_val)
            elif isinstance(value, dict):
                try:
                    global_dict[key] = orjson.loads(config_val)
                except Exception:
                    pass
            else:
                try:
                    global_dict[key] = int(config_val)
                except Exception:
                    global_dict[key] = config_val
            if isinstance(global_dict[key], list):
                global_dict[key] = tuple(global_dict[key])
    try:
        with open("core/config.py", "r") as config_file:
            for node in ast.parse(config_file.read()).body:
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Name):
                    target_id = node.targets[0].id
                    value_id = node.value.id
                    if target_id.startswith("config_") and value_id.startswith("config_") and os.getenv(target_id) is None:
                        global_dict[target_id] = global_dict[value_id]
    except Exception:
        pass
    return None