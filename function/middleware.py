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
        print(traceback.format_exc())
    if sentry_dsn:
        import sentry_sdk
        sentry_sdk.capture_exception(exception)
    return error_msg, responses.JSONResponse(status_code=400, content={"status": 0, "message": error_msg})

async def func_api_log_create(*, config_is_log_api: int, api_id: int, request: any, response: any, time_ms: int, user_id: any, func_postgres_object_create: callable, client_postgres_pool: any, func_postgres_serialize: callable, cache_postgres_schema: dict, cache_postgres_buffer: dict, config_table: dict) -> None:
    """Log API request details asynchronously if enabled in config (identifier validated)."""
    if config_is_log_api == 0:
        return None
    log_obj = {
        "created_by_id": user_id,
        "type": 1,
        "ip_address": request.client.host if request.client else None,
        "api": request.url.path,
        "api_id": api_id,
        "method": request.method,
        "query_param": str(request.query_params),
        "status_code": response.status_code if hasattr(response, "status_code") else None,
        "response_time_ms": time_ms
    }
    await func_postgres_object_create(client_postgres_pool=client_postgres_pool, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, mode="buffer", table="log_api", obj_list=[log_obj], is_serialize=0, buffer_limit=config_table.get("log_api", {}).get("buffer", 100), cache_postgres_buffer=cache_postgres_buffer)
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

async def func_check_is_active(*, user_dict: dict, url_path: str, config_api: dict, client_postgres_pool: any, client_redis: any, cache_users_is_active: dict, config_redis_cache_ttl_sec: int) -> None:
    """Check if the user is active using a strictly configured mode from config_api."""
    cfg = config_api.get(url_path, {}).get("user_is_active_check")
    if not cfg or not user_dict:
        return None
    mode, active_flag = cfg
    if active_flag == 0:
        return None
    async def fetch_is_active(uid):
        async with client_postgres_pool.acquire() as conn:
            rows = await conn.fetch("select id,is_active from users where id=$1", uid)
        if not rows:
            raise Exception("user not found")
        return rows[0]["is_active"]
    if mode == "redis":
        if not client_redis:
            raise Exception("redis client missing")
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
    if active_status == "absent":
        raise Exception("missing is_active")
    if active_status == 0:
        raise Exception("user not active")

async def func_check_admin(*, user_dict: dict, url_path: str, config_api: dict, client_postgres_pool: any, client_redis: any, cache_users_role: dict, config_redis_cache_ttl_sec: int) -> None:
    """Ensure sufficient roles to access admin endpoints using a strictly configured mode from config_api."""
    if not url_path.startswith("/admin") or not (cfg := config_api.get(url_path)) or "user_role_check" not in cfg:
        return None
    mode = cfg["user_role_check"][0]
    roles = set(cfg["user_role_check"][1])
    async def fetch_role(uid):
        async with client_postgres_pool.acquire() as conn:
            rows = await conn.fetch("select role from users where id=$1", uid)
        if not rows:
            raise Exception("user not found")
        return rows[0]["role"]
    if mode == "redis":
        if not client_redis:
            raise Exception("redis client missing")
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
    if user_role == "absent":
        raise Exception("user role missing")
    if user_role is None or user_role == "":
        raise Exception("user role is null")
    if user_role == "role":
        raise Exception("user role is invalid")
    if not isinstance(user_role, int):
        try:
            user_role = int(user_role)
        except Exception:
            raise Exception("invalid user role type")
    if user_role not in roles:
        raise Exception("access denied")

async def func_check_cache(*, mode: str, url_path: str, query_params: dict, config_api: dict, client_redis: any, user_id: int, response: any, cache_api_response: dict) -> any:
    """Retrieve from or store to cache API responses based on configuration."""
    from fastapi import Response
    import gzip, base64, time
    if mode not in ["get", "set"]:
        raise Exception(f"invalid cache mode: {mode}")
    uid = user_id if "my/" in url_path else 0
    cache_key = f"""cache:{url_path}?{"&".join(f"{k}={v}" for k, v in sorted(query_params.items()))}:{uid}"""
    api_cfg = config_api.get(url_path, {})
    cache_mode, expire_sec = api_cfg.get("api_cache_sec", (None, None))
    if not (expire_sec is not None and expire_sec > 0):
        return None if mode == "get" else response
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

async def func_api_response(*, request: any, api_function: callable, config_api: dict, client_redis: any, user_id: int, func_background: callable, func_cache: callable, cache_api_response: dict) -> tuple:
    """Orchestrate API request handling, including background task delegation and cache management."""
    from fastapi import responses
    path = request.url.path
    query_params = dict(request.query_params)
    api_cfg = config_api.get(path, {})
    cache_sec_config = api_cfg.get("api_cache_sec")
    response = None
    resp_type = 0
    if query_params.get("is_background") == "1":
        body_bytes = await request.body()
        response = await func_background(scope=request.scope, body_bytes=body_bytes, api_function=api_function)
        resp_type = 1
    elif cache_sec_config:
        response = await func_cache(mode="get", url_path=path, query_params=query_params, config_api=config_api, client_redis=client_redis, user_id=user_id, response=None, cache_api_response=cache_api_response)
        if response:
            resp_type = 2
    if not response:
        response = await api_function(request)
        resp_type = 3
        if cache_sec_config:
            response = await func_cache(mode="set", url_path=path, query_params=query_params, config_api=config_api, client_redis=client_redis, user_id=user_id, response=response, cache_api_response=cache_api_response)
            resp_type = 4
    return response, resp_type

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

