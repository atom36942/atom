async def func_middleware_check_auth(*, headers: dict, url_path: str, config_token_secret_key: str, config_api_namespace_auth: list) -> dict:
    """Unified authentication: extracts Bearer token, validates presence for protected routes, and decodes JWT. Returns the decoded user dict or an empty dict."""
    auth_header = headers.get("Authorization")
    token = auth_header.split("Bearer ", 1)[1] if auth_header and auth_header.startswith("Bearer ") else None
    if token:
        import jwt, orjson
        decoded_payload = jwt.decode(token, config_token_secret_key, algorithms="HS256")
        user_obj = orjson.loads(decoded_payload["data"])
    else:
        user_obj = {}
        if url_path.startswith(tuple(config_api_namespace_auth)):
            raise Exception("authorization token missing")
    return user_obj

async def func_middleware_check_is_active(*, user_dict: dict, url_path: str, config_api: dict, client_postgres_pool: any, client_redis: any, cache_users_is_active: dict, config_redis_cache_ttl_sec: int) -> None:
    """Check if the user is active using a strictly configured mode from config_api."""
    cfg = config_api.get(url_path, {}).get("user_is_active_check")
    if not cfg or not user_dict: return None
    mode, active_flag = cfg
    if active_flag == 0: return None
    async def fetch_is_active(uid):
        if not client_postgres_pool: raise Exception("postgres client missing")
        async with client_postgres_pool.acquire() as conn:
            rows = await conn.fetch("select id,is_active from users where id=$1", uid)
        if not rows: raise Exception("user not found")
        return rows[0]["is_active"]
    if mode == "redis":
        if not client_redis: raise Exception("redis client missing")
        cache_key = f"""cache:user:active:{user_dict["id"]}"""
        active_status = None
        cached_val = await client_redis.get(cache_key)
        if cached_val is not None:
            active_status = int(cached_val)
        else:
            active_status = await fetch_is_active(user_dict["id"])
            await client_redis.setex(cache_key, config_redis_cache_ttl_sec, str(active_status))
    elif mode == "realtime":
        active_status = await fetch_is_active(user_dict["id"])
    elif mode == "inmemory":
        active_status = cache_users_is_active.get(user_dict["id"])
        if active_status is None:
            active_status = await fetch_is_active(user_dict["id"])
    elif mode == "token":
        active_status = user_dict.get("is_active", "absent")
    else:
        raise Exception(f"invalid mode: {mode}, allowed: redis, realtime, inmemory, token")
    if active_status == "absent": raise Exception("missing is_active")
    if active_status == 0: raise Exception("user not active")

async def func_middleware_check_is_deleted(*, user_dict: dict, url_path: str, config_api: dict, client_postgres_pool: any, client_redis: any, cache_users_is_deleted: dict, config_redis_cache_ttl_sec: int) -> None:
    """Check if the user is deleted using a strictly configured mode from config_api."""
    cfg = config_api.get(url_path, {}).get("user_is_deleted_check")
    if not cfg or not user_dict: return None
    mode, deleted_flag = cfg
    if deleted_flag == 0: return None
    async def fetch_is_deleted(uid):
        if not client_postgres_pool: raise Exception("postgres client missing")
        async with client_postgres_pool.acquire() as conn:
            rows = await conn.fetch("select id,is_deleted from users where id=$1", uid)
        if not rows: raise Exception("user not found")
        return rows[0]["is_deleted"]
    if mode == "redis":
        if not client_redis: raise Exception("redis client missing")
        cache_key = f"""cache:user:deleted:{user_dict["id"]}"""
        deleted_status = None
        cached_val = await client_redis.get(cache_key)
        if cached_val is not None:
            deleted_status = int(cached_val)
        else:
            deleted_status = await fetch_is_deleted(user_dict["id"])
            await client_redis.setex(cache_key, config_redis_cache_ttl_sec, str(deleted_status))
    elif mode == "realtime":
        deleted_status = await fetch_is_deleted(user_dict["id"])
    elif mode == "inmemory":
        deleted_status = cache_users_is_deleted.get(user_dict["id"])
        if deleted_status is None:
            deleted_status = await fetch_is_deleted(user_dict["id"])
    elif mode == "token":
        deleted_status = user_dict.get("is_deleted", "absent")
    else:
        raise Exception(f"invalid mode: {mode}, allowed: redis, realtime, inmemory, token")
    if deleted_status == "absent": raise Exception("missing is_deleted")
    if deleted_status == 1: raise Exception("user is deleted")

async def func_middleware_check_role(*, user_dict: dict, url_path: str, config_api: dict, client_postgres_pool: any, client_redis: any, cache_users_role: dict, config_redis_cache_ttl_sec: int) -> None:
    """Ensure sufficient roles to access endpoints using a strictly configured mode from config_api."""
    if not url_path.startswith("/admin") or not (cfg := config_api.get(url_path)) or "user_role_check" not in cfg:
        return None
    mode = cfg["user_role_check"][0]
    roles = set(cfg["user_role_check"][1])
    async def fetch_role(uid):
        if not client_postgres_pool: raise Exception("postgres client missing")
        async with client_postgres_pool.acquire() as conn:
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

async def func_middleware_check_ratelimiter(*, client_redis: any, config_api: dict, url_path: str, identifier: str, cache_ratelimiter: dict) -> None:
    """Check and enforce API rate limits using either Redis or in-memory storage."""
    import time
    api_cfg = config_api.get(url_path, {})
    rl_config = api_cfg.get("api_ratelimiting_times_sec")
    if not rl_config: return None
    mode, limit, window = rl_config
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

async def func_middleware_api_cache_get(*, path: str, query_params: dict, config_api: dict, client_redis: any, user_id: int, cache_api_response: dict, config_api_namespace_user: list) -> any:
    """Check for cached response in Redis or in-memory. Returns a Response object if hit, else None."""
    from fastapi import Response
    import gzip, base64, time
    cfg = config_api.get(path, {}).get("api_cache_sec")
    if not cfg or cfg[1] <= 0: return None
    uid = user_id if path.startswith(tuple(config_api_namespace_user)) else 0
    key = f"cache:{path}?{'&'.join(f'{k}={v}' for k, v in sorted(query_params.items()))}:{uid}"
    data = await client_redis.get(key) if cfg[0] == "redis" else (item["data"] if (item := cache_api_response.get(key)) and item["expire_at"] > time.time() else None)
    return Response(content=gzip.decompress(base64.b64decode(data)).decode(), status_code=200, media_type="application/json", headers={"x-cache": "hit"}) if data else None

async def func_middleware_api_background(*, scope: dict, body_bytes: bytes, api_function: callable) -> any:
    """Delegate the request execution to a background task and return a standard acknowledgment."""
    from fastapi import Request, responses
    from starlette.background import BackgroundTask
    async def receive(): return {"type": "http.request", "body": body_bytes}
    async def task(): await api_function(Request(scope=scope, receive=receive))
    resp = responses.JSONResponse(status_code=200, content={"status": 1, "message": "added in background"})
    resp.background = BackgroundTask(task)
    return resp

async def func_middleware_api_cache_set(*, path: str, query_params: dict, response: any, config_api: dict, client_redis: any, user_id: int, cache_api_response: dict, config_api_namespace_user: list) -> any:
    """Compress and store the response in the configured cache (Redis or in-memory)."""
    from fastapi import Response
    import gzip, base64, time
    cfg = config_api.get(path, {}).get("api_cache_sec")
    if not cfg or cfg[1] <= 0: return response
    body = getattr(response, "body", None) or b"".join([chunk async for chunk in response.body_iterator])
    comp = base64.b64encode(gzip.compress(body)).decode()
    uid = user_id if path.startswith(tuple(config_api_namespace_user)) else 0
    key = f"cache:{path}?{'&'.join(f'{k}={v}' for k, v in sorted(query_params.items()))}:{uid}"
    if cfg[0] == "redis": await client_redis.setex(key, cfg[1], comp)
    else: cache_api_response[key] = {"data": comp, "expire_at": time.time() + cfg[1]}
    return Response(content=body, status_code=response.status_code, media_type=response.media_type, headers=dict(response.headers))

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
    
async def func_request_param_read(*, request: any, mode: str, strict: int, config: list) -> dict:
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
    if config is None: return params_dict
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
    for param in config:
        if not isinstance(param, (list, tuple)): raise Exception(f"invalid configuration format: expected list or tuple, got {type(param)}")
        param_len = len(param)
        if param_len < 5:
            param_key = param[0] if param_len > 0 else "unknown"
            raise Exception(f"invalid config tuple length {param_len} for '{param_key}': (key, dtype, is_mandatory, allowed_values, default_value) are required")
        key, dtype, is_mandatory, allowed_values, default_value = param[0], param[1], int(param[2]), param[3], param[4]
        if dtype not in TYPE_MAP and not dtype.startswith("list:"): raise Exception(f"parameter '{key}' has invalid dtype '{dtype}'")
        if is_mandatory == 1 and default_value is not None: raise Exception(f"parameter '{key}' is mandatory, default_value must be None")
        if default_value is not None and allowed_values and default_value not in allowed_values:
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
        if val is not None and allowed_values and val not in allowed_values: raise Exception(f"parameter '{key}' value not allowed, allowed: {allowed_values}")
        output_dict[key] = val
    return output_dict


def func_openapi_spec_generate(*, app_routes: list, config_api_namespace_auth: list, app_state: any) -> dict:
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
            if any(path.startswith(x) for x in config_api_namespace_auth):
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

def func_app_router_add(*, app: any, router_dir: any, router_order: dict) -> None:
    """Load router modules from a directory in a configured order and include their routers."""
    import importlib.util, pathlib
    router_dir = pathlib.Path(router_dir)
    router_paths = sorted(router_dir.glob("*.py"), key=lambda path: (router_order.get(path.stem, 100), path.stem))
    for router_path in router_paths:
        if router_path.name.startswith(("_", ".")): continue
        spec = importlib.util.spec_from_file_location(f"core.router.{router_path.stem}", router_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "router"): app.include_router(module.router)
    return None

def func_config_override_from_env(*, global_dict: dict) -> None:
    import orjson, os, ast, contextlib; from dotenv import load_dotenv
    load_dotenv(".env")
    for k, v in list(global_dict.items()):
        if k.startswith("config_") and (ev := os.getenv(k)) is not None:
            if isinstance(v, bool): global_dict[k] = 1 if ev.lower() in ("true", "1", "yes", "on", "ok") else 0
            elif isinstance(v, (list, tuple, dict)):
                with contextlib.suppress(Exception): global_dict[k] = orjson.loads(ev)
            else: global_dict[k] = int(ev) if ev.lstrip("-").isdigit() else ev
            if isinstance(global_dict[k], list): global_dict[k] = tuple(global_dict[k])
    with contextlib.suppress(Exception):
        for n in ast.parse(open("core/config.py", encoding="utf-8").read()).body:
            if isinstance(n, ast.Assign) and len(n.targets)==1 and (t:=getattr(n.targets[0], "id", "")).startswith("config_") and (v:=getattr(n.value, "id", "")).startswith("config_") and os.getenv(t) is None: global_dict[t] = global_dict.get(v)
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

async def func_postgres_schema_read(*, client_postgres_pool: any) -> dict:
    """Read full PostgreSQL schema (including tables, views, and materialized views) from public namespace."""
    sql = """
        SELECT 
            c.relname AS table_name,
            a.attname AS column_name,
            format_type(a.atttypid, a.atttypmod) AS data_type,
            CASE WHEN a.attnotnull THEN 'NO' ELSE 'YES' END AS is_nullable,
            pg_get_expr(d.adbin, d.adrelid) AS column_default
        FROM pg_class c
        JOIN pg_attribute a ON c.oid = a.attrelid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        LEFT JOIN pg_attrdef d ON d.adrelid = c.oid AND d.adnum = a.attnum
        WHERE n.nspname = 'public' 
          AND c.relkind IN ('r', 'v', 'm')
          AND a.attnum > 0 
          AND NOT a.attisdropped
        ORDER BY c.relname, a.attnum;
    """
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(sql)
    schema = {}
    for r in records:
        schema.setdefault(r["table_name"], {})[r["column_name"]] = {"datatype": r["data_type"], "is_nullable": r["is_nullable"], "default": r["column_default"]}
    return schema

async def func_postgres_map_column(*, client_postgres_pool: any, config_sql: str) -> dict:
    """Execute a mapping SQL query and return a dictionary from the first two columns."""
    if not config_sql: return {}
    async with client_postgres_pool.acquire() as conn:
        rows = await conn.fetch(config_sql)
    return {r[0]: r[1] for r in rows}

async def func_postgres_schema_init(*, client_postgres_pool: any, client_password_hasher: any, config_postgres: dict, config_root_user_password: str) -> str:
    """Initialize PostgreSQL database schema, tables, indexes, constraints, and triggers based on configuration."""
    if not config_postgres: raise Exception("config_postgres missing")
    if "table" not in config_postgres: raise Exception("config_postgres.table missing")
    control = config_postgres.get("control", {})
    is_ext, is_autovacuum = control.get("is_enable_extension", 0), control.get("is_enable_autovacuum_optimize", 0)
    is_drop_schema, is_drop_table, is_truncate_table = control.get("is_disable_drop_schema", 0), control.get("is_disable_drop_table", 0), control.get("is_disable_truncate", 0)
    is_disable_drop_column = control.get("is_disable_drop_column", 1)
    is_enable_drop_column_mismatch = control.get("is_enable_drop_column_mismatch", control.get("is_drop_column_mismatch_db", control.get("is_drop_column_mismatch", control.get("is_enable_drop_column", 0))))
    if is_disable_drop_column and is_enable_drop_column_mismatch:
        raise Exception("config_postgres.control conflict: is_disable_drop_column=1 blocks is_enable_drop_column_mismatch=1")
    bulk_blocked = control.get("table_delete_disable_row_bulk", control.get("disable_table_delete_row_bulk", []))
    table_blocked = control.get("table_delete_disable_row", control.get("disable_table_delete_row", []))
    catalog = {"idx": set(), "uni": set(), "chk": set(), "tg": set()}
    for key, val in config_postgres.get("sql", {}).items():
        if key == "index" and isinstance(val, dict):
            for idx_name in val.keys():
                catalog["idx"].add(idx_name)
        elif isinstance(key, str) and key.startswith("index_"):
            catalog["idx"].add(key[6:])
    reserved = {"all", "analyze", "and", "any", "as", "asc", "asymmetric", "authorization", "binary", "both", "case", "cast", "check", "collate", "collation", "column", "concurrently", "constraint", "create", "cross", "current_catalog", "current_date", "current_role", "current_schema", "current_time", "current_timestamp", "current_user", "default", "deferrable", "desc", "distinct", "do", "else", "end", "except", "false", "fetch", "for", "foreign", "freeze", "from", "full", "grant", "group", "having", "ilike", "in", "initially", "inner", "intersect", "into", "is", "isnull", "join", "lateral", "leading", "left", "like", "limit", "localtime", "localtimestamp", "natural", "not", "notnull", "null", "offset", "on", "only", "or", "order", "outer", "overlaps", "placing", "primary", "references", "returning", "right", "select", "session_user", "similar", "some", "symmetric", "table", "tablesample", "then", "to", "trailing", "true", "union", "unique", "user", "using", "variadic", "verbose", "when", "where", "window", "with"}
    for table_name, column_configs in config_postgres["table"].items():
        column_names = {col["name"] for col in column_configs if "name" in col}
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
    async with client_postgres_pool.acquire() as conn:
        if is_ext:
            extensions = config_postgres.get("extension", [])
            for extension in extensions:
                try:
                    await conn.execute(f'CREATE EXTENSION IF NOT EXISTS "{extension}";')
                except Exception as e:
                    if any(x in str(e).lower() for x in ("insufficient_privilege", "permission denied", "must be superuser")) or "pg_cron" in extension:
                        print(f"⚠️  {f'extension {extension}':<30} : ❌ skipped (insufficient privileges)")
                    else:
                        raise e
        try:
            if is_disable_drop_column:
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
        for table_name, column_configs in config_postgres["table"].items():
            await conn.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" (id BIGSERIAL PRIMARY KEY);')
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
            for col_cfg in column_configs:
                col_name = col_cfg["name"]
                col_type = col_cfg["datatype"]
                if col_name not in current_cols:
                    old_name = col_cfg.get("old")
                    if old_name and old_name in current_cols:
                        await conn.execute(f'ALTER TABLE "{table_name}" RENAME COLUMN "{old_name}" TO "{col_name}"')
                        current_cols[col_name] = current_cols.pop(old_name)
                        current_notnulls[col_name] = current_notnulls.pop(old_name)
                        table_changed = True
                    else:
                        default_val = f"""DEFAULT {col_cfg["default"]}""" if "default" in col_cfg else ""
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
                    target_default = str(col_cfg.get("default")).strip() if "default" in col_cfg else None
                    current_default = current_defaults.get(col_name)
                    if target_default:
                        if current_default is None or target_default not in current_default:
                             await conn.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN "{col_name}" SET DEFAULT {target_default}')
                             table_changed = True
                    elif current_default is not None:
                        await conn.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN "{col_name}" DROP DEFAULT')
                        table_changed = True
            if is_enable_drop_column_mismatch:
                desired_cols = {"id"} | {col_cfg["name"] for col_cfg in column_configs}
                for col_name in list(current_cols):
                    if col_name not in desired_cols:
                        await conn.execute(f'ALTER TABLE "{table_name}" DROP COLUMN "{col_name}"')
                        table_changed = True
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
                                ops = ""
                                if index_type == "gin" and len(index_cols) == 1:
                                    if index_cols[0] == col_name and "text" in col_type.lower() and "[]" not in col_type.lower():
                                        ops = "gin_trgm_ops"
                                cols_joined = ", ".join(index_cols)
                                if ops:
                                    await conn.execute(f'CREATE INDEX "{idx_name}" ON "{table_name}" USING {index_type}("{index_cols[0]}" {ops});')
                                else:
                                    cols_quoted = ", ".join([f'"{c}"' for c in index_cols])
                                    await conn.execute(f'CREATE INDEX "{idx_name}" ON "{table_name}" USING {index_type}({cols_quoted});')
                                table_changed = True
                if "in" in col_cfg:
                    chk_name = f"check_{table_name}_{col_name}_in_{get_hash(col_cfg['in'])}"
                    catalog["chk"].add(chk_name)
                    if chk_name not in existing_meta:
                        await conn.execute(f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{chk_name}" CHECK ("{col_name}" IN {col_cfg["in"]});')
                        table_changed = True
                if "regex" in col_cfg:
                    regex_name = f"check_{table_name}_{col_name}_regex_{get_hash(col_cfg['regex'])}"
                    catalog["chk"].add(regex_name)
                    if regex_name not in existing_meta:
                        await conn.execute(f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{regex_name}" CHECK ("{col_name}" ~ \'{col_cfg["regex"]}\');')
                        table_changed = True
                if "check" in col_cfg:
                    vld_name = f"check_{table_name}_{col_name}_vld_{get_hash(col_cfg['check'])}"
                    catalog["chk"].add(vld_name)
                    if vld_name not in existing_meta:
                        await conn.execute(f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{vld_name}" CHECK ({col_cfg["check"]});')
                        table_changed = True
                if col_cfg.get("unique"):
                    for group in col_cfg["unique"].split("|"):
                        unique_cols = [x.strip() for x in group.split(",")]
                        uni_name = f"""unique_{table_name}_{"_".join(unique_cols)}"""
                        catalog["uni"].add(uni_name)
                        if uni_name not in existing_meta:
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
            catalog["tg"].add("trigger_protect_root_users")
            await conn.execute("CREATE OR REPLACE FUNCTION func_protect_root_users() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF TG_OP = 'DELETE' THEN IF OLD.id = 1 THEN RAISE EXCEPTION 'DELETE not allowed for root user (id=1)'; END IF; RETURN OLD; ELSIF TG_OP = 'UPDATE' THEN IF OLD.id = 1 THEN IF NEW.type IS DISTINCT FROM OLD.type OR NEW.username IS DISTINCT FROM OLD.username OR NEW.role IS DISTINCT FROM OLD.role OR NEW.is_active IS DISTINCT FROM OLD.is_active THEN RAISE EXCEPTION 'Updates to type, username, role, or is_active are not allowed for root user (id=1)'; END IF; END IF; RETURN NEW; END IF; RETURN NULL; END; $$; DROP TRIGGER IF EXISTS trigger_protect_root_users ON users; CREATE TRIGGER trigger_protect_root_users BEFORE UPDATE OR DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_protect_root_users();")
            if all(c in users_cols for c in ("type", "username", "password", "role", "is_active")):
                root_user_password_hash = client_password_hasher.hash(config_root_user_password)
                await conn.execute("INSERT INTO users (type, username, password, role, is_active) VALUES (1, 'atom', $1, 1, 1) ON CONFLICT (username, type) DO UPDATE SET role = 1, is_active = 1 WHERE users.role IS DISTINCT FROM 1 OR users.is_active IS DISTINCT FROM 1;", root_user_password_hash)
            if "password" in users_cols and "log_users_password" in db_tables:
                catalog["tg"].add("trigger_password_log_users")
                await conn.execute("CREATE OR REPLACE FUNCTION func_password_log_users() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.password IS DISTINCT FROM NEW.password THEN INSERT INTO log_users_password (user_id, password) VALUES (NEW.id, NEW.password); END IF; RETURN NEW; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_password_log_users ON users; CREATE TRIGGER trigger_password_log_users AFTER UPDATE ON users FOR EACH ROW EXECUTE FUNCTION func_password_log_users();")
            if control.get("is_enable_users_delete_child_soft", 0) and "is_deleted" in users_cols:
                catalog["tg"].add("trigger_soft_delete_users")
                await conn.execute("CREATE OR REPLACE FUNCTION func_soft_delete_users() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE r RECORD; v INTEGER; BEGIN v := (CASE WHEN NEW.is_deleted=1 THEN 1 ELSE 0 END); FOR r IN SELECT table_schema, table_name, column_name FROM information_schema.columns WHERE column_name IN ('created_by_id', 'user_id') AND table_name NOT IN ('users', 'spatial_ref_sys') AND table_schema NOT IN ('information_schema', 'pg_catalog') LOOP IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = r.table_schema AND table_name = r.table_name AND column_name = 'is_deleted') THEN EXECUTE format('UPDATE %I.%I SET is_deleted = $1 WHERE %I = $2', r.table_schema, r.table_name, r.column_name) USING v, NEW.id; END IF; END LOOP; RETURN NEW; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_soft_delete_users ON users; CREATE TRIGGER trigger_soft_delete_users AFTER UPDATE ON users FOR EACH ROW WHEN (OLD.is_deleted IS DISTINCT FROM NEW.is_deleted) EXECUTE FUNCTION func_soft_delete_users();")
            if control.get("is_enable_users_delete_child_hard", 0):
                catalog["tg"].add("trigger_hard_delete_users")
                await conn.execute("CREATE OR REPLACE FUNCTION func_hard_delete_users() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE r RECORD; BEGIN FOR r IN SELECT table_schema, table_name, column_name FROM information_schema.columns WHERE column_name IN ('created_by_id', 'user_id') AND table_name NOT IN ('users', 'spatial_ref_sys') AND table_schema NOT IN ('information_schema', 'pg_catalog') LOOP EXECUTE format('DELETE FROM %I.%I WHERE %I = $1', r.table_schema, r.table_name, r.column_name) USING OLD.id; END LOOP; RETURN OLD; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_hard_delete_users ON users; CREATE TRIGGER trigger_hard_delete_users AFTER DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_hard_delete_users();")
            if control.get("is_disable_users_delete_role", 0) and "role" in users_cols:
                catalog["tg"].add("trigger_delete_disable_role_users")
                await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_role_users() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.role IS NOT NULL THEN RAISE EXCEPTION 'DELETE not allowed for user with role'; END IF; RETURN OLD; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_delete_disable_role_users ON users; CREATE TRIGGER trigger_delete_disable_role_users BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_delete_disable_role_users();")
            if control.get("is_enable_users_set_deleted_at", 0) and "is_deleted" in users_cols and "deleted_at" in users_cols:
                catalog["tg"].add("trigger_set_deleted_at_users")
                await conn.execute("CREATE OR REPLACE FUNCTION func_set_deleted_at_users() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.is_deleted = 1 THEN NEW.deleted_at := NOW(); ELSE NEW.deleted_at := NULL; END IF; RETURN NEW; END; $$;")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_set_deleted_at_users ON users; CREATE TRIGGER trigger_set_deleted_at_users BEFORE UPDATE ON users FOR EACH ROW WHEN (OLD.is_deleted IS DISTINCT FROM NEW.is_deleted) EXECUTE FUNCTION func_set_deleted_at_users();")
                catalog["tg"].add("trigger_set_deleted_at_insert_users")
                await conn.execute("DROP TRIGGER IF EXISTS trigger_set_deleted_at_insert_users ON users; CREATE TRIGGER trigger_set_deleted_at_insert_users BEFORE INSERT ON users FOR EACH ROW WHEN (NEW.is_deleted = 1) EXECUTE FUNCTION func_set_deleted_at_users();")
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
        for key, query in config_postgres.get("sql", {}).items():
            if key == "index" and isinstance(query, dict):
                for idx_name, idx_query in query.items():
                    if isinstance(idx_query, str) and idx_query.strip():
                        await conn.execute(idx_query)
            elif isinstance(query, str) and query.strip():
                await conn.execute(query)
    return "database init done"

async def func_postgres_serialize(*, client_postgres_pool: any, client_password_hasher: any, cache_postgres_schema: dict, table: str, obj_list: list, is_base: int) -> list:
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
        if "bool" in t: return vs.lower() in ("true", "1", "yes", "on", "ok")
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
            if val is None:
                new_item[col] = val
                continue
            new_item[col] = serialize_val(val, schema[col]["datatype"])
        output_list.append(new_item)
    return output_list

async def func_postgres_where_build(*, client_postgres_pool: any, client_password_hasher: any, func_postgres_serialize: callable, cache_postgres_schema: dict, table: str, filter: list, prefix: str = "") -> tuple:
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
        serialized = await func_postgres_serialize(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, cache_postgres_schema=schema_override or cache_postgres_schema, table=table, obj_list=obj_list, is_base=is_base_type)
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

async def func_postgres_relation(*, client_postgres_pool: any, client_postgres_conn: any = None, obj_list: list, relation: list, config_relation_fetch_limit_max: int) -> list:
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
        client = client_postgres_conn or client_postgres_pool
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
            if custom_limit > config_relation_fetch_limit_max: raise Exception(f"relation fetch limit {custom_limit} exceeds maximum allowed: {config_relation_fetch_limit_max}")
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

async def func_postgres_create(*, client_postgres_pool: any, client_postgres_conn: any, client_password_hasher: any, func_postgres_serialize: callable, func_regex_check: callable, cache_postgres_schema: dict, cache_postgres_buffer_create: dict, config_regex: dict, config_table: dict, config_obj_list_limit: int, config_buffer_limit: int, mode: str, table: str, obj_list: list) -> any:
    """Create PostgreSQL records with support for buffering, batch insertion, and dynamic serialization."""
    import re, orjson
    async def insert_serialized(tbl, serialized_list):
        columns = [c for c in serialized_list[0] if re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(c)) or (_ for _ in ()).throw(Exception(f"invalid identifier {c}"))]
        cols_sql = ",".join([f'"{c}"' for c in columns])
        if len(serialized_list) == 1:
            placeholders = ",".join([f"${i+1}" for i in range(len(columns))])
            sql = f'INSERT INTO "{tbl}" ({cols_sql}) VALUES ({placeholders}) RETURNING id;'
            args = [serialized_list[0][c] for c in columns]
            if client_postgres_conn: ids = await client_postgres_conn.fetch(sql, *args)
            else:
                async with client_postgres_pool.acquire() as conn: ids = await conn.fetch(sql, *args)
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
            limit_chunk = 5000
            async def _execute_bulk(connection):
                for i in range(0, len(serialized_list), limit_chunk):
                    batch = serialized_list[i : i + limit_chunk]
                    sql = f'INSERT INTO "{tbl}" ({col_list}) SELECT {cast_list} FROM jsonb_to_recordset($1::jsonb) AS x({def_list}) RETURNING id'
                    ids_batch = await connection.fetch(sql, orjson.dumps(batch, default=str).decode('utf-8'))
                    all_ids.extend([dict(r) for r in ids_batch])
            if client_postgres_conn:
                await _execute_bulk(client_postgres_conn)
            else:
                async with client_postgres_pool.acquire() as conn:
                    await _execute_bulk(conn)
            ids = all_ids
        return [r["id"] for r in ids] if ids and "id" in ids[0] else "created"
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
    if config_obj_list_limit and len(obj_list) > config_obj_list_limit: raise Exception(f"maximum {config_obj_list_limit} objects allowed")
    if table == "spatial_ref_sys": raise Exception("system table protected")
    if table == "users": await func_regex_check(config_regex=config_regex, obj_list=obj_list)
    serialized_list = await func_postgres_serialize(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=obj_list, is_base=0 if len(obj_list) > 1 else 1)
    if mode == "buffer":
        key = f"{table}|{','.join(sorted(serialized_list[0].keys()))}"
        cache_postgres_buffer_create.setdefault(key, []).extend(serialized_list)
        if len(cache_postgres_buffer_create[key]) >= config_buffer_limit:
            items = cache_postgres_buffer_create[key]
            await insert_serialized(table, items)
            cache_postgres_buffer_create[key] = []
            return "buffered released"
        return "buffered"
    if mode == "now":
        return await insert_serialized(table, serialized_list)

async def func_postgres_read(*, client_postgres_pool: any, client_password_hasher: any, func_postgres_serialize: callable, func_postgres_where_build: callable, func_postgres_relation: callable, cache_postgres_schema: dict, config_relation_fetch_limit_max: int, table: str, filter: list, limit: int, page: int, order: str, column: str, relation: list) -> list:
    """Powerful generic PostgreSQL object reader with complex filtering, sorting, pagination, and relation fetching."""
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)): raise Exception(f"invalid identifier {table}")
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
    where_statement, values = await func_postgres_where_build(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, table=table, filter=filters, prefix="")
    bind_idx = len(values) + 1
    sql_select = f'SELECT {column_list} FROM "{table}" {where_statement} ORDER BY {order_clause} LIMIT ${bind_idx} OFFSET ${bind_idx+1}'
    values.extend([limit, (page - 1) * limit])
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(sql_select, *values)
        result_list = [dict(r) for r in records]
        if relation and result_list:
            result_list = await func_postgres_relation(client_postgres_pool=client_postgres_pool, client_postgres_conn=conn, obj_list=result_list, relation=relation, config_relation_fetch_limit_max=config_relation_fetch_limit_max)
        return result_list

async def func_postgres_update(*, client_postgres_pool: any, client_postgres_conn: any, client_password_hasher: any, func_postgres_serialize: callable, func_regex_check: callable, cache_postgres_schema: dict, config_regex: dict, config_table: dict, config_obj_list_limit: int, table: str, obj_list: list, created_by_id: int) -> any:
    """Update PostgreSQL records immediately with support for owner validation and dynamic serialization."""
    import re
    if not obj_list: raise Exception("object list required")
    if len(obj_list) == 1 and not obj_list[0]: raise Exception("object data required")
    if any(not isinstance(obj, dict) for obj in obj_list): raise Exception("object data invalid")
    if config_obj_list_limit and len(obj_list) > config_obj_list_limit: raise Exception(f"maximum {config_obj_list_limit} objects allowed")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)): raise Exception(f"invalid identifier {table}")
    if table == "spatial_ref_sys": raise Exception("system table protected")
    if table == "users": await func_regex_check(config_regex=config_regex, obj_list=obj_list)
    obj_list = await func_postgres_serialize(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=obj_list, is_base=1)
    if any("id" not in obj for obj in obj_list): raise Exception("missing required field: 'id' for update operation")
    update_cols = [c for c in obj_list[0] if c != "id" and (re.match(r"^[a-zA-Z0-9_\s\(\)\-\.]+$", str(c)) or (_ for _ in ()).throw(Exception(f"invalid identifier {c}")))]
    if not update_cols: raise Exception("update field required")
    if any(set(obj.keys()) != set(obj_list[0].keys()) for obj in obj_list): raise Exception("object keys mismatch")
    returned_ids = []
    if len(obj_list) == 1:
        async def _execute_one(connection):
            obj = obj_list[0]
            batch_vals = [obj[col] for col in update_cols]
            set_clause = ", ".join([f'"{col}"=${i+1}' for i, col in enumerate(update_cols)])
            where_clause = f'"id"=${len(batch_vals)+1}'
            batch_vals.append(obj["id"])
            if created_by_id is not None:
                where_clause += f' AND "created_by_id"=${len(batch_vals)+1}'
                batch_vals.append(created_by_id)
            sql = f'UPDATE "{table}" SET {set_clause} WHERE {where_clause} RETURNING id;'
            ids = await connection.fetch(sql, *batch_vals)
            return [r["id"] for r in ids] if ids else []
        if client_postgres_conn: return await _execute_one(client_postgres_conn)
        async with client_postgres_pool.acquire() as conn: return await _execute_one(conn)
    limit_batch = 5000
    actual_batch_size = max(1, limit_batch // (len(update_cols) + (2 if created_by_id is not None else 1)))
    async def _execute_update(connection):
        async with connection.transaction():
            for i in range(0, len(obj_list), actual_batch_size):
                batch = obj_list[i:i+actual_batch_size]
                batch_vals, set_clauses = [], []
                for col in update_cols:
                    case_statements = []
                    for obj in batch:
                        batch_vals.extend([obj["id"], obj[col]])
                        if created_by_id is not None:
                            batch_vals.append(created_by_id)
                            case_statements.append(f'WHEN "id"=${len(batch_vals)-2}::bigint AND "created_by_id"=${len(batch_vals)}::bigint THEN ${len(batch_vals)-1}')
                        else: case_statements.append(f'WHEN "id"=${len(batch_vals)-1}::bigint THEN ${len(batch_vals)}')
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
        async with client_postgres_pool.acquire() as conn: await _execute_update(conn)
    return returned_ids if returned_ids else "updated"

async def func_postgres_delete(*, client_postgres_pool: any, client_postgres_conn: any, table: str, ids: list, created_by_id: int) -> str:
    """Delete records by ID with optional ownership and system table restrictions (identifier validated)."""
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)): raise Exception(f"invalid identifier {table}")
    if table == "users": raise Exception("users table not allowed")
    if ids and isinstance(ids, (list, tuple)):
        ids_str = ",".join(str(int(x)) for x in ids)
    else:
        ids_str = "0" # Safe fallback that matches nothing if list is empty or invalid
    sql_delete = f'DELETE FROM "{table}" WHERE "id" IN ({ids_str}) AND ($1::bigint IS NULL OR "created_by_id"=$1);'
    if table == "spatial_ref_sys": raise Exception("system table protected")
    if client_postgres_conn:
        await client_postgres_conn.execute(sql_delete, created_by_id)
    else:
        async with client_postgres_pool.acquire() as conn:
            await conn.execute(sql_delete, created_by_id)
    return "ids deleted"

async def func_producer(*, queue: str, client_celery_producer: any, client_kafka_producer: any, client_rabbitmq_producer: any, client_redis_producer: any, channel: str, payload: dict) -> any:
    """Ultra-standardized producer orchestration. Handles multi-tech dispatch with explicit clients."""
    import orjson
    if not queue: raise Exception("invalid queue format: queue missing")
    allowed_queue = ["redis", "rabbitmq", "kafka", "celery"]
    if queue not in allowed_queue: raise Exception(f"invalid queue: {queue}. allowed: {allowed_queue}")
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

async def func_token_encode(*, user: dict, config_token_secret_key: str, config_token_expiry_sec: int, config_token_refresh_expiry_sec: int, config_token_key: list) -> dict:
    """Generate access and refresh JWT tokens for a user object."""
    import jwt, orjson, time
    if user is None: return None
    payload_dict = {k: user.get(k) for k in config_token_key} if config_token_key else dict(user) if isinstance(user, dict) else user
    serialized_payload = orjson.dumps(payload_dict, default=str).decode("utf-8")
    now_ts = int(time.time())
    access_token = jwt.encode({"exp": now_ts + config_token_expiry_sec, "data": serialized_payload, "type": "access"}, config_token_secret_key)
    refresh_token = jwt.encode({"exp": now_ts + config_token_refresh_expiry_sec, "data": serialized_payload, "type": "refresh"}, config_token_secret_key)
    return {"token": access_token, "token_refresh": refresh_token, "token_expiry_sec": config_token_expiry_sec, "token_refresh_expiry_sec": config_token_refresh_expiry_sec}

async def func_otp_generate(*, client_postgres_pool: any, email: str, mobile: str, config_otp_length: int) -> int:
    """Generate a random OTP and store it in PostgreSQL for a given email or mobile."""
    import random
    otp = random.randint(10**(config_otp_length-1), 10**config_otp_length - 1)
    sql = "INSERT INTO otp (otp, email, mobile) VALUES ($1, $2, $3);"
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(sql, otp, email.strip().lower() if email else None, mobile.strip() if mobile else None)
    return otp

async def func_otp_verify(*, client_postgres_pool: any, otp: int, email: str, mobile: str, config_expiry_sec_otp: int) -> None:
    """Verify an OTP for email or mobile within its expiration window."""
    if not otp: raise Exception("otp code missing")
    if not email and not mobile: raise Exception("missing both email and mobile")
    if email and mobile: raise Exception("provide only one identifier")
    if email:
        sql = f"SELECT otp, (created_at > CURRENT_TIMESTAMP - INTERVAL '{config_expiry_sec_otp}s') as is_active FROM otp WHERE email=$1 ORDER BY id DESC LIMIT 1"
        identifier = email.strip().lower()
    else:
        sql = f"SELECT otp, (created_at > CURRENT_TIMESTAMP - INTERVAL '{config_expiry_sec_otp}s') as is_active FROM otp WHERE mobile=$1 ORDER BY id DESC LIMIT 1"
        identifier = mobile.strip()
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(sql, identifier)
        if not records: raise Exception("otp not found")
        if records[0]["otp"] != otp: raise Exception("invalid otp code")
        if not records[0]["is_active"]: raise Exception("otp code expired")
    return "done"

async def func_api_file_to_chunks(*, upload_file: any, chunk_size: int):
    """Generator: reads an uploaded CSV file in chunks and yields lists of dictionaries."""
    import csv, io
    content = await upload_file.read()
    f = io.StringIO(content.decode("utf-8"))
    reader = csv.DictReader(f)
    chunk = []
    for row in reader:
        chunk.append(row)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    if chunk: yield chunk

async def func_user_read_single(*, client_postgres_pool: any, user_id: int) -> dict:
    """Read a single user by ID from PostgreSQL, raises Exception if not found."""
    async with client_postgres_pool.acquire() as conn:
        record = await conn.fetchrow("SELECT * FROM users WHERE id=$1;", user_id)
    if not record: raise Exception("user not found")
    return dict(record)

def func_check(*, app_routes: list, config_config_path: str, config_function_path: str, config_api_namespace: list, config_router_path: str, config_api: dict, config_mode_user: list, config_mode_api: list, config_postgres: dict, config_func_check: dict = None) -> None:
    if config_func_check is None:
        config_func_check = {}
    if config_func_check.get("is_check_config_api", 1) == 1:
        api_ids = []
        for path, cfg in config_api.items():
            if (api_id := cfg.get("id")):
                if api_id in api_ids: raise Exception(f"duplicate api id: {api_id}")
                api_ids.append(api_id)
            for key in ("user_role_check", "user_is_active_check"):
                if (mode_cfg := cfg.get(key)) and mode_cfg[0] not in config_mode_user: raise Exception(f"invalid mode: {mode_cfg[0]} in {path} ({key}), allowed: {config_mode_user}")
            for key in ("api_ratelimiting_times_sec", "api_cache_sec"):
                if (mode_cfg := cfg.get(key)) and mode_cfg[0] not in config_mode_api: raise Exception(f"invalid mode: {mode_cfg[0]} in {path} ({key}), allowed: {config_mode_api}")
        route_paths = {route.path for route in app_routes if hasattr(route, "path")}
        for path in config_api.keys():
            if path not in route_paths: raise Exception(f"unused configuration in config_api: {path} (route not found)")
    if config_func_check.get("is_check_route_admin_rules", 1) == 1:
        for route in app_routes:
            if not hasattr(route, "path") or not hasattr(route, "endpoint"): continue
            path = route.path
            if path.startswith("/admin"):
                if path not in config_api: raise Exception(f"admin route '{path}' missing in config_api")
                if "user_role_check" not in config_api[path]: raise Exception(f"admin route '{path}' missing 'user_role_check' in config_api")
                if 1 not in config_api[path]["user_role_check"][1]: raise Exception(f"admin route '{path}' must allow role 1")
    if config_func_check.get("is_check_route_namespace_rules", 1) == 1:
        for route in app_routes:
            if not hasattr(route, "path"): continue
            path = route.path
            segments = path.split("/")
            if path == "/":
                route_ns = "/"
            elif len(segments) <= 2 or not any(segments[2:]):
                route_ns = "/"
            else:
                route_ns = f"/{segments[1]}/"
            if route_ns not in config_api_namespace:
                raise Exception(f"invalid route: {path}")
    if config_func_check.get("is_check_route_endpoint_naming", 1) == 1:
        for route in app_routes:
            if not hasattr(route, "path") or not hasattr(route, "endpoint"): continue
            path, endpoint_name = route.path, route.endpoint.__name__
            if not endpoint_name.startswith("func_api_"): raise Exception(f"invalid endpoint function name: {endpoint_name} in {path}")
    if config_func_check.get("is_check_config_naming", 1) == 1:
        import ast
        if config_config_path:
            with open(config_config_path if config_config_path.endswith(".py") else f"{config_config_path}.py", "r", encoding="utf-8") as f: tree = ast.parse(f.read())
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        targets_to_check = [target]
                        while targets_to_check:
                            t = targets_to_check.pop()
                            if isinstance(t, ast.Name) and not t.id.startswith("config_"): raise Exception(f"invalid config variable name: {t.id}")
                            if isinstance(t, (ast.Tuple, ast.List)): targets_to_check.extend(t.elts)
                elif isinstance(node, ast.AnnAssign):
                    if isinstance(node.target, ast.Name) and not node.target.id.startswith("config_"): raise Exception(f"invalid config variable name: {node.target.id}")
    if config_func_check.get("is_check_function_naming", 1) == 1:
        import ast
        if config_function_path:
            with open(config_function_path if config_function_path.endswith(".py") else f"{config_function_path}.py", "r", encoding="utf-8") as f: tree = ast.parse(f.read())
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("func_"): raise Exception(f"invalid function name: {node.name}")
    if config_func_check.get("is_check_router_declaration", 1) == 1:
        import ast, pathlib
        if config_router_path:
            router_dir = pathlib.Path(config_router_path)
            for router_path in router_dir.glob("*.py"):
                if router_path.name.startswith(("_", ".")): continue
                with open(router_path, "r", encoding="utf-8") as f: tree = ast.parse(f.read())
                if not any(isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "router" for target in node.targets) for node in tree.body): raise Exception(f"router file '{router_path.name}' missing 'router' variable")
    if config_func_check.get("is_check_config_postgres", 1) == 1:
        if config_postgres and "table" in config_postgres:
            global_column_types = {}
            for table_name, columns in config_postgres["table"].items():
                if not table_name or not table_name.strip(): raise Exception("table name cannot be empty")
                column_names_list = [col.get("name") for col in columns if "name" in col]
                if len(column_names_list) != len(set(column_names_list)):
                    seen = set()
                    for name in column_names_list:
                        if name in seen: raise Exception(f"duplicate column name '{name}' in table '{table_name}'")
                        seen.add(name)
                column_names = set(column_names_list)
                if ("created_by_id" in column_names or "user_id" in column_names) and "is_deleted" not in column_names: raise Exception(f"Table '{table_name}' has 'created_by_id' or 'user_id' but is missing the 'is_deleted' column required for soft deletes.")
                btrees, others = [], []
                for col in columns:
                    col_name, col_type = col.get("name"), col.get("datatype")
                    if not col_name or not col_name.strip(): raise Exception(f"column name in {table_name} cannot be empty")
                    if not col_type or not col_type.strip(): raise Exception(f"datatype in {table_name}.{col_name} cannot be empty")
                    if col_name in global_column_types and global_column_types[col_name] != col_type:
                        raise Exception(f"datatype mismatch for column '{col_name}': '{col_type}' in {table_name} vs '{global_column_types[col_name]}' elsewhere")
                    global_column_types[col_name] = col_type
                    if (col_unique := col.get("unique")):
                        for group in (x.strip() for x in col_unique.split("|")):
                            u_cols = [c.strip() for c in group.split(",")]
                            for uc in u_cols:
                                if uc not in column_names: raise Exception(f"unique constraint in {table_name}.{col_name} references non-existent column '{uc}'")
                            if col_name not in u_cols: raise Exception(f"unique constraint in {table_name}.{col_name} does not include '{col_name}' itself")
                            btrees.append((u_cols, True, col_name))
                    if (col_index := col.get("index")):
                        for group in (x.strip() for x in col_index.split("|")):
                            if "(" in group and group.endswith(")"):
                                idx_type, cols_str = group[:-1].split("(", 1)
                                idx_type, idx_cols = idx_type.strip().lower(), [c.strip() for c in cols_str.split(",")]
                                for ic in idx_cols:
                                    if ic not in column_names: raise Exception(f"index in {table_name}.{col_name} references non-existent column '{ic}'")
                                if col_name not in idx_cols: raise Exception(f"index in {table_name}.{col_name} does not include '{col_name}' itself")
                                if idx_type == "btree": btrees.append((idx_cols, False, col_name))
                                else: others.append((idx_type, idx_cols, col_name))
                            else: raise Exception(f"invalid index syntax '{group}' in {table_name}.{col_name}")
                for i, (c1, u1, o1) in enumerate(btrees):
                    for j, (c2, u2, o2) in enumerate(btrees):
                        if i == j: continue
                        if c1 == c2 and u1 == u2: raise Exception(f"duplicate {'unique' if u1 else 'btree index'} on {table_name}: {c1}")
                        if not u1 and c2[:len(c1)] == c1: raise Exception(f"redundant btree index on {table_name}.{o1}({','.join(c1)}) covered by {'unique' if u2 else 'btree'} on {o2}({','.join(c2)})")
                        if u1 and u2 and c1[:len(c2)] == c2: raise Exception(f"redundant unique constraint on {table_name}.{o1}({','.join(c1)}) - {o2}({','.join(c2)}) is already unique")
                for i, (t1, c1, o1) in enumerate(others):
                    for j, (t2, c2, o2) in enumerate(others):
                        if i == j: continue
                        if t1 == t2 and c1 == c2: raise Exception(f"duplicate {t1} index on {table_name}: {c1}")
    return None

