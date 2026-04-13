def func_openapi_spec_generate(*, app_routes: list, config_api_roles_auth: list, app_state: any) -> dict:
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
            if any(path.startswith(x) for x in config_api_roles_auth):
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
                        p_loc = None
                        p_list = None
                        for kw in node.keywords:
                            if kw.arg == "mode": p_loc = eval_node(kw.value)
                            elif kw.arg == "config": p_list = eval_node(kw.value)
                        if p_loc is None and len(node.args) > 1: p_loc = eval_node(node.args[1])
                        if p_list is None and len(node.args) > 2: p_list = eval_node(node.args[2])
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
                                    rgx_pat = p[5][0] if len(p) > 5 and isinstance(p[5], (list, tuple)) and len(p[5]) > 0 else None
                                    rgx_err = p[5][1] if len(p) > 5 and isinstance(p[5], (list, tuple)) and len(p[5]) > 1 else None
                                    p_desc = p[6] if len(p) > 6 else None
                                    op["parameters"].append({
                                    "name": p[0],
                                    "in": p_loc,
                                    "description": ". ".join([str(x) for x in [rgx_err, p_desc] if x]) if rgx_err or p_desc else None,
                                    "required": bool(p[2]) if len(p) > 2 else False,
                                    "schema": {
                                        "type": tp,
                                        "format": fmt,
                                        **({"items": itms} if itms else {}),
                                        "enum": p[3] if len(p) > 3 and isinstance(p[3], (list, tuple)) else None,
                                        "default": p[4] if len(p) > 4 else None,
                                        "pattern": rgx_pat
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
                                    rgx_pat = p[5][0] if len(p) > 5 and isinstance(p[5], (list, tuple)) and len(p[5]) > 0 else None
                                    rgx_err = p[5][1] if len(p) > 5 and isinstance(p[5], (list, tuple)) and len(p[5]) > 1 else None
                                    p_desc = p[6] if len(p) > 6 else None
                                    props[p[0]] = {
                                        "type": tp,
                                        "format": fmt,
                                        **({"items": itms} if itms else {}),
                                        "enum": p[3] if len(p) > 3 and isinstance(p[3], (list, tuple)) else None,
                                        "default": p[4] if len(p) > 4 else None,
                                        "pattern": rgx_pat,
                                        "description": ". ".join([str(x) for x in [rgx_err, p_desc] if x]) if rgx_err or p_desc else None
                                    }
                                    if len(p) > 2 and bool(p[2]):
                                        schema_obj["required"].append(p[0])
                    except Exception:
                        pass
            except Exception:
                pass

            spec["paths"][path][m_lower] = op
    return spec