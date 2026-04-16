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
                                op["parameters"].append({
                                    "name": p[0], "in": p_loc, "required": bool(p[2]) if len(p) > 2 else False,
                                    "description": ". ".join([str(x) for x in [p[5][1] if len(p) > 5 and isinstance(p[5], (list, tuple)) and len(p[5]) > 1 else None, p[6] if len(p) > 6 else None] if x]) or None,
                                    "schema": {"type": tp, "format": "binary" if dt == "file" else None, **({"items": itms} if itms else {}), "enum": p[3] if len(p) > 3 and isinstance(p[3], (list, tuple)) else None, "default": p[4] if len(p) > 4 else None, "pattern": p[5][0] if len(p) > 5 and isinstance(p[5], (list, tuple)) and len(p[5]) > 0 else None}
                                })
                        elif p_list is not None and p_loc in ["body", "form"]:
                            media_type = "application/json" if p_loc == "body" else "multipart/form-data"
                            if "requestBody" not in op: op["requestBody"] = {"content": {media_type: {"schema": {"type": "object", "properties": {}, "required": []}}}}
                            props, reqs = op["requestBody"]["content"][media_type]["schema"]["properties"], op["requestBody"]["content"][media_type]["schema"]["required"]
                            for p in p_list:
                                if not p or not isinstance(p, (list, tuple)) or len(p) < 1: continue
                                dt = p[1] if len(p) > 1 else "str"
                                props[p[0]] = {"type": TYPE_MAP.get(dt.split(":")[0], "string"), "format": "binary" if dt == "file" else None, **({"items": {"type": TYPE_MAP.get(dt.split(":")[1], "string")}} if ":" in dt else {}), "enum": p[3] if len(p) > 3 and isinstance(p[3], (list, tuple)) else None, "default": p[4] if len(p) > 4 else None, "pattern": p[5][0] if len(p) > 5 and isinstance(p[5], (list, tuple)) and len(p[5]) > 0 else None, "description": ". ".join([str(x) for x in [p[5][1] if len(p) > 5 and isinstance(p[5], (list, tuple)) and len(p[5]) > 1 else None, p[6] if len(p) > 6 else None] if x]) or None}
                                if len(p) > 2 and bool(p[2]): reqs.append(p[0])
                    except: pass
            except: pass
            spec["paths"][path][m_lower] = op
            
    return spec
