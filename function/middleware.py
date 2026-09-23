"""Atom middleware functions."""

from .request import func_query_bool_parse

async def func_middleware_check_active(*, is_active: bool = True) -> None:
    """Check whether current API endpoint is active/enabled."""
    if not is_active: raise Exception("API endpoint is disabled")
    return None

async def func_middleware_check_token(*, user_dict: dict, url_path: str, is_token: bool = False, user_check_role: list = None, user_check_deactivated: list = None, user_check_deleted: list = None) -> None:
    """Check whether current API requires token-authenticated user."""
    is_token_required = is_token or bool(user_check_role) or bool(user_check_deactivated) or bool(user_check_deleted)
    if is_token_required:
        if not user_dict: raise Exception("authorization token missing")
        token_type = user_dict.get("_token_type") if isinstance(user_dict, dict) else None
        if url_path == "/my/token-refresh":
            if token_type != "refresh": raise Exception("refresh token required")
        elif token_type != "access":
            raise Exception("access token required")
    return None

async def func_middleware_check_user_deactivated(*, user_dict: dict, user_check_deactivated: any, client_postgres: any, client_redis: any, cache_users_deactivated: dict, config_redis_cache_ttl_sec: int) -> None:
    """Check if the user is deactivated using a strictly configured mode from config_api."""
    cfg = user_check_deactivated
    if not cfg or not user_dict: return None
    mode = cfg.get("mode") if isinstance(cfg, dict) else (cfg[0] if isinstance(cfg, (list, tuple)) else None)
    if not mode: return None
    async def fetch_deactivated_status(uid):
        if not client_postgres: raise Exception("postgres client missing")
        async with client_postgres.acquire() as conn:
            rows = await conn.fetch("select id, deactivated_at from users where id=$1", uid)
        if not rows: raise Exception("user not found")
        return rows[0]["deactivated_at"]
    if mode == "redis":
        if not client_redis: raise Exception("redis client missing")
        cache_key = f"""cache:user:active:{user_dict["id"]}"""
        active_status = None
        cached_val = await client_redis.get(cache_key)
        if cached_val is not None:
            active_status = cached_val if cached_val != 'None' else None
        else:
            active_status = await fetch_deactivated_status(user_dict["id"])
            await client_redis.setex(cache_key, config_redis_cache_ttl_sec, str(active_status))
    elif mode == "realtime":
        active_status = await fetch_deactivated_status(user_dict["id"])
    elif mode == "inmemory":
        active_status = cache_users_deactivated.get(user_dict["id"], "absent")
        if active_status == "absent":
            active_status = await fetch_deactivated_status(user_dict["id"])
    elif mode == "token":
        active_status = user_dict.get("deactivated_at", "absent")
    else:
        raise Exception(f"invalid mode: {mode}, allowed: redis, realtime, inmemory, token")
    if active_status == "absent": raise Exception("missing deactivated_at")
    if active_status is not None: raise Exception("user not active")

async def func_middleware_check_user_deleted(*, user_dict: dict, user_check_deleted: any, client_postgres: any, client_redis: any, cache_users_deleted: dict, config_redis_cache_ttl_sec: int) -> None:
    """Check if the user is deleted using a strictly configured mode from config_api."""
    cfg = user_check_deleted
    if not cfg or not user_dict: return None
    mode = cfg.get("mode") if isinstance(cfg, dict) else (cfg[0] if isinstance(cfg, (list, tuple)) else None)
    if not mode: return None
    async def fetch_deleted(uid):
        if not client_postgres: raise Exception("postgres client missing")
        async with client_postgres.acquire() as conn:
            rows = await conn.fetch("select deleted_at from users where id=$1", uid)
        if not rows: raise Exception("user not found")
        return rows[0]["deleted_at"]
    if mode == "redis":
        if not client_redis: raise Exception("redis client missing")
        cache_key = f"""cache:user:deleted_at:{user_dict["id"]}"""
        deleted_status = None
        cached_val = await client_redis.get(cache_key)
        if cached_val is not None:
            deleted_status = cached_val if cached_val != "None" else None
        else:
            deleted_status = await fetch_deleted(user_dict["id"])
            await client_redis.setex(cache_key, config_redis_cache_ttl_sec, str(deleted_status))
    elif mode == "realtime":
        deleted_status = await fetch_deleted(user_dict["id"])
    elif mode == "inmemory":
        deleted_status = cache_users_deleted.get(user_dict["id"], "absent")
        if deleted_status == "absent":
            deleted_status = await fetch_deleted(user_dict["id"])
    elif mode == "token":
        deleted_status = user_dict.get("deleted_at", "absent")
    else:
        raise Exception(f"invalid mode: {mode}, allowed: redis, realtime, inmemory, token")
    if deleted_status == "absent": raise Exception("missing deleted_at")
    if deleted_status is not None: raise Exception("user is deleted")

async def func_middleware_check_role(*, user_dict: dict, user_check_role: any, client_postgres: any, client_redis: any, cache_users_role: dict, config_redis_cache_ttl_sec: int) -> None:
    """Ensure sufficient roles to access endpoints using a strictly configured mode from config_api."""
    cfg = user_check_role
    if not cfg: return None
    if not user_dict: raise Exception("authorization token missing")
    if isinstance(cfg, dict):
        mode = cfg.get("mode")
        raw_roles = cfg.get("roles", [])
    elif isinstance(cfg, (list, tuple)):
        mode = cfg[0]
        raw_roles = cfg[1]
    else:
        return None
    roles = {int(role) for role in raw_roles}
    async def fetch_role(uid):
        if not client_postgres: raise Exception("postgres client missing")
        async with client_postgres.acquire() as conn:
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

async def func_middleware_check_ratelimiter(*, client_redis: any, rate_limit: any = None, api_ratelimiting_times_sec: any = None, url_path: str, identifier: str, cache_ratelimiter: dict) -> None:
    """Check and enforce API rate limits using either Redis or in-memory storage."""
    import time
    rl_config = rate_limit if rate_limit is not None else api_ratelimiting_times_sec
    if not rl_config: return None
    if isinstance(rl_config, dict):
        mode = rl_config.get("mode")
        limit = rl_config.get("limit", 0)
        window = rl_config.get("window_sec", 0)
    elif isinstance(rl_config, (list, tuple)):
        mode, limit, window = rl_config
    else:
        return None
    limit, window = int(limit), int(window)
    if limit <= 0 or window <= 0: return None
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

async def func_middleware_api_cache(*, mode: str, path: str, query_params: dict, cache: any = None, api_cache_sec: any = None, client_redis: any = None, user_id: int = 0, cache_api_response: dict = None, response: any = None) -> any:
    """Get or set middleware API cache for a request."""
    from fastapi import Response
    import gzip, base64, time
    if mode not in ("get", "set"): raise Exception(f"invalid cache operation: {mode}, allowed: get, set")
    cfg = cache if cache is not None else api_cache_sec
    if isinstance(cfg, dict):
        cache_mode = cfg.get("mode")
        ttl = int(cfg.get("ttl_sec", 0))
        is_user_cache = cfg.get("is_per_user", cfg.get("is_user_cache", cfg.get("stale_sec", 0)))
    elif isinstance(cfg, (list, tuple)):
        cache_mode = cfg[0] if cfg else None
        ttl = int(cfg[1]) if cfg else 0
        is_user_cache = cfg[2] if cfg else 0
    else:
        cache_mode, ttl, is_user_cache = None, 0, 0
    is_user_cache = str(is_user_cache) == "1" or is_user_cache is True
    is_disable_cache = func_query_bool_parse(query_params.get("is_disable_cache"), default=False)
    is_enabled = not is_disable_cache and bool(cfg) and bool(cache_mode) and ttl > 0
    if mode == "set" and not is_enabled: return response
    if mode == "get" and not is_enabled: return None
    if cache_api_response is None: cache_api_response = {}
    uid = user_id if is_user_cache else 0
    key = f"cache:{path}?{'&'.join(f'{k}={v}' for k, v in sorted(query_params.items()))}:{uid}"
    if mode == "get":
        data = await client_redis.get(key) if cache_mode == "redis" else (item["data"] if (item := cache_api_response.get(key)) and item["expire_at"] > time.time() else None)
        return Response(content=gzip.decompress(base64.b64decode(data)).decode(), status_code=200, media_type="application/json", headers={"x-cache": "hit"}) if data else None
    body = getattr(response, "body", None) or b"".join([chunk async for chunk in response.body_iterator])
    comp = base64.b64encode(gzip.compress(body)).decode()
    if cache_mode == "redis": await client_redis.setex(key, ttl, comp)
    else: cache_api_response[key] = {"data": comp, "expire_at": time.time() + ttl}
    response = Response(content=body, status_code=response.status_code, media_type=response.media_type, headers=dict(response.headers))
    response.is_cache_set = True
    return response

async def func_middleware_api_background(*, scope: dict, body_bytes: bytes, api_function: callable) -> any:
    """Delegate the request execution to a background task and return a standard acknowledgment."""
    import asyncio
    from fastapi import Request, responses
    async def receive(): return {"type": "http.request", "body": body_bytes}
    async def task():
        try:
            await api_function(Request(scope=scope, receive=receive))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"❌ background api error: {e}")
    task_obj = asyncio.create_task(task())
    app = scope.get("app")
    task_set = getattr(getattr(app, "state", None), "runtime_background_tasks", None) if app else None
    if task_set is not None:
        task_set.add(task_obj)
        task_obj.add_done_callback(task_set.discard)
    resp = responses.JSONResponse(status_code=200, content={"status": 1, "message": "added in background"})
    return resp

def func_middleware_log_query_params(*, query_params: any) -> str:
    """Keep routine query metadata while redacting credentials and opaque payloads."""
    import re
    from urllib.parse import urlencode, parse_qsl
    items = query_params.multi_items() if hasattr(query_params, "multi_items") else parse_qsl(str(query_params), keep_blank_values=True)
    sensitive = re.compile(r"password|passwd|secret|token|authorization|credential|api.?key|access.?key|signature|(?:^|_)(?:otp|code|dsn|sql|url|urls|filter|payload|question|sig)(?:$|_)", re.IGNORECASE)
    return urlencode([(key, "[REDACTED]" if sensitive.search(key) else value) for key, value in items])

def _redact_error_message(message):
    import re
    message = re.sub(r"(\b[a-z][a-z0-9+.-]*://)[^/\s@]+@", r"\1[REDACTED]@", message, flags=re.IGNORECASE)
    message = re.sub(r"\bBearer\s+[^\s,;]+", "Bearer [REDACTED]", message, flags=re.IGNORECASE)
    return re.sub(r"((?:password|passwd|secret|token|api[_-]?key|access[_-]?key|sig)\s*[=:]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s&;,]+)", r"\1[REDACTED]", message, flags=re.IGNORECASE)

async def func_middleware_api_response_error(*, exception: Exception, is_traceback: bool, sentry_dsn: str) -> tuple:
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
    elif isinstance(exception, asyncpg.PostgresError):
        error_msg = "database request failed"
    elif isinstance(exception, botocore.exceptions.ClientError):
        error_msg = f"""cloud service error: {exception.response.get("Error", {}).get("Code", "Unknown")}"""
    elif isinstance(exception, redis.exceptions.RedisError):
        error_msg = "cache service error"
    elif isinstance(exception, jwt.exceptions.PyJWTError):
        error_msg = "authentication token invalid"
    elif isinstance(exception, httpx.HTTPStatusError):
        error_msg = f"external api error: {exception.response.status_code}"
    elif isinstance(exception, httpx.RequestError):
        error_msg = "external service request failed"
    else:
        error_msg = str(exception)
    error_msg = _redact_error_message(error_msg)
    if is_traceback:
        import sys
        traceback.print_tb(exception.__traceback__)
        print(f"{type(exception).__name__}: {error_msg}", file=sys.stderr)
    if sentry_dsn:
        import sentry_sdk
        sentry_sdk.capture_exception(exception)
    return error_msg, responses.JSONResponse(status_code=400, content={"status": 0, "message": error_msg})

def func_middleware_security_headers(*, response: any) -> any:
    """Attach baseline HTTP security headers to response."""
    if hasattr(response, "headers"):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-XSS-Protection", "0")
    return response
