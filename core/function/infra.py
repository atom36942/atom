async def func_authenticate(*, headers: dict, url_path: str, config_token_secret_key: str, config_api_roles_auth: list) -> dict:
    """Unified authentication: extracts Bearer token, validates presence for protected routes, and decodes JWT. Returns the decoded user dict or an empty dict."""
    auth_header = headers.get("Authorization")
    token = auth_header.split("Bearer ", 1)[1] if auth_header and auth_header.startswith("Bearer ") else None
    if token:
        import jwt, orjson
        decoded_payload = jwt.decode(token, config_token_secret_key, algorithms="HS256")
        user_obj = orjson.loads(decoded_payload["data"])
    else:
        user_obj = {}
        if url_path.startswith(tuple(config_api_roles_auth)):
            raise Exception("authorization token missing")
    return user_obj

async def func_check_is_active(*, user_dict: dict, url_path: str, config_api: dict, client_postgres_pool: any, client_redis: any, cache_users_is_active: dict, config_redis_cache_ttl_sec: int) -> None:
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

async def func_check_role(*, user_dict: dict, url_path: str, config_api: dict, client_postgres_pool: any, client_redis: any, cache_users_role: dict, config_redis_cache_ttl_sec: int) -> None:
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

async def func_check_ratelimiter(*, client_redis_ratelimiter: any, config_api: dict, url_path: str, identifier: str, cache_ratelimiter: dict) -> None:
    """Check and enforce API rate limits using either Redis or in-memory storage."""
    import time
    api_cfg = config_api.get(url_path, {})
    rl_config = api_cfg.get("api_ratelimiting_times_sec")
    if not rl_config: return None
    mode, limit, window = rl_config
    cache_key = f"ratelimiter:{url_path}:{identifier}"
    if mode == "redis":
        if not client_redis_ratelimiter: raise Exception("redis client missing")
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

async def func_check_cache(*, mode: str, url_path: str, query_params: dict, config_api: dict, client_redis: any, user_id: int, response: any, cache_api_response: dict) -> any:
    """Retrieve from or store to cache API responses based on configuration."""
    from fastapi import Response
    import gzip, base64, time
    if mode not in ["get", "set"]:
        raise Exception(f"invalid cache mode: {mode}")
    uid = user_id if url_path.startswith("/my/") else 0
    cache_key = f"""cache:{url_path}?{"&".join(f"{k}={v}" for k, v in sorted(query_params.items()))}:{uid}"""
    api_cfg = config_api.get(url_path, {})
    cache_mode, expire_sec = api_cfg.get("api_cache_sec", (None, None))
    if not (expire_sec is not None and expire_sec > 0):
        return None if mode == "get" else response
    if cache_mode == "redis" and not client_redis:
        raise Exception("redis client missing")
    if mode == "get":
        cached_data = None
        if cache_mode == "redis":
            cached_data = await client_redis.get(cache_key)
        elif cache_mode == "inmemory":
            item = cache_api_response.get(cache_key)
            if item and item["expire_at"] > time.time():
                cached_data = item["data"]
        if cached_data:
            return Response(content=gzip.decompress(base64.b64decode(cached_data)).decode(), status_code=200, media_type="application/json", headers={"x-cache": "hit"})
        return None
    elif mode == "set":
        body_content = getattr(response, "body", None)
        if body_content is None:
            body_content = b"".join([chunk async for chunk in response.body_iterator])
        compressed_body = base64.b64encode(gzip.compress(body_content)).decode()
        if cache_mode == "redis":
            await client_redis.setex(cache_key, expire_sec, compressed_body)
        elif cache_mode == "inmemory":
            cache_api_response[cache_key] = {"data": compressed_body, "expire_at": time.time() + expire_sec}
        return Response(content=body_content, status_code=response.status_code, media_type=response.media_type, headers=dict(response.headers))

async def func_api_response_background(*, scope: dict, body_bytes: bytes, api_function: callable) -> any:
    """Execute an API function in the background and return a 200 response immediately."""
    from fastapi import Request, responses
    from starlette.background import BackgroundTask
    async def receive_provider(): return {"type": "http.request", "body": body_bytes}
    async def api_task_execution():
        new_request = Request(scope=scope, receive=receive_provider)
        await api_function(new_request)
    background_resp = responses.JSONResponse(status_code=200, content={"status": 1, "message": "added in background"})
    background_resp.background = BackgroundTask(api_task_execution)
    return background_resp

async def func_api_response(*, request: any, api_function: callable, config_api: dict, client_redis: any, user_id: int, func_background: callable, func_cache: callable, cache_api_response: dict) -> any:
    """Orchestrate API request handling, including background task delegation and cache management."""
    path = request.url.path
    query_params = dict(request.query_params)
    api_cfg = config_api.get(path, {})
    cache_sec_config = api_cfg.get("api_cache_sec")
    response = None
    if query_params.get("is_background") == "1":
        body_bytes = await request.body()
        response = await func_background(scope=request.scope, body_bytes=body_bytes, api_function=api_function)
    elif cache_sec_config:
        response = await func_cache(mode="get", url_path=path, query_params=query_params, config_api=config_api, client_redis=client_redis, user_id=user_id, response=None, cache_api_response=cache_api_response)
    if not response:
        response = await api_function(request)
        if cache_sec_config:
            response = await func_cache(mode="set", url_path=path, query_params=query_params, config_api=config_api, client_redis=client_redis, user_id=user_id, response=response, cache_api_response=cache_api_response)
    return response

async def func_api_response_error(*, exception: Exception, is_traceback: int, sentry_dsn: str) -> tuple:
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
        error_msg = (column[-1].replace("_", " ") + " required") if column else "missing required field"
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

async def func_api_log_create(*, config_is_enable_log_api: int, api_id: int, request: any, response: any, time_ms: int, user_id: any, description: str, func_postgres_create: callable, client_postgres_pool: any, client_password_hasher: any, func_postgres_serialize: callable, cache_postgres_schema: dict, cache_postgres_buffer: dict, config_table: dict) -> None:
    """Log API request details asynchronously if enabled in config (identifier validated)."""
    if config_is_enable_log_api == 0 or client_postgres_pool is None: return None
    log_obj = {
        "created_by_id": user_id,
        "type": 1,
        "ip_address": request.client.host if request.client else None,
        "api": request.url.path,
        "api_id": api_id,
        "method": request.method,
        "query_param": str(request.query_params),
        "status_code": response.status_code if hasattr(response, "status_code") else None,
        "response_time_ms": time_ms,
        "description": description
    }
    await func_postgres_create(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, mode="buffer", table="log_api", obj_list=[log_obj], is_serialize=0, buffer_limit=config_table.get("log_api", {}).get("buffer", 100), cache_postgres_buffer=cache_postgres_buffer, client_postgres_conn=None)
    return None

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
        if isinstance(v, str) and v.strip():
            try:
                return orjson.loads(v)
            except Exception:
                pass
        return {}
    TYPE_MAP = {
        "int": int, "bigint": int, "smallint": int, "integer": int, "int4": int, "int8": int,
        "float": float, "number": float, "numeric": float,
        "str": str, "any": lambda v: v, 
        "bool": lambda v: 1 if str(v).strip().lower() in ("1", "true", "yes", "on", "ok") else 0, 
        "dict": smart_dict, "object": smart_dict,
        "file": lambda v: [x for x in (v if isinstance(v, list) else [v] if v is not None else []) if hasattr(x, "file")],
        "list": lambda v: [] if v is None else v if isinstance(v, list) else [] if (isinstance(v, str) and not v.strip()) else [x.strip() for x in v.split(",") if x.strip()] if isinstance(v, str) else [v]
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
        if not allowed: return []
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
        if not pool: return []
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
    if api_roles_auth is not None and not isinstance(api_roles_auth, (list, tuple)): raise Exception("config_api_roles_auth must be a list")
    app_paths = {route.path for route in app_routes if hasattr(route, "path")}
    async def _get_root_user_errors(pool):
        if not pool: return []
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
    if errors: raise Exception("; ".join(errors))
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
    """Override configuration variables starting with 'config_' from environment variables and .env file."""
    import orjson, os, ast; from dotenv import load_dotenv; from pathlib import Path
    load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")
    for k, v in list(global_dict.items()):
        if k.startswith("config_") and (ev := os.getenv(k)) is not None:
            if isinstance(v, bool): global_dict[k] = 1 if ev.lower() in ("true", "1", "yes", "on", "ok") else 0
            elif isinstance(v, (list, tuple, dict)):
                try: global_dict[k] = orjson.loads(ev)
                except: pass
            else:
                try: global_dict[k] = int(ev)
                except: global_dict[k] = ev
            if isinstance(global_dict[k], list): global_dict[k] = tuple(global_dict[k])
    try:
        with open("core/config.py") as f:
            for n in [n for n in ast.parse(f.read()).body if isinstance(n, ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Name)]:
                t, v = n.targets[0].id, n.value.id
                if t.startswith("config_") and v.startswith("config_") and os.getenv(t) is None: global_dict[t] = global_dict.get(v)
    except: pass
    return None
