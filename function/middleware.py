# import
import asyncio
import gzip
import ipaddress
import re
import secrets
import sys
import time
import traceback
from typing import Any
from urllib.parse import parse_qsl
from urllib.parse import urlencode
import asyncpg
import httpx
import jwt.exceptions
import redis.exceptions
from fastapi import Request
from fastapi import Response
from fastapi import responses
from fastapi.routing import APIRoute
from starlette.routing import compile_path
from starlette.routing import Match
from redis.asyncio import Redis
from .background import func_runtime_error_record
from .request import func_query_bool_parse
from .request import func_request_form_close

# function
def func_api_error(*, message: str, status_code: int) -> Exception:
    """Build an exception that func_middleware_api_response_error returns with this HTTP status; a plain Exception stays 400."""
    error = Exception(message)
    error.status_code = status_code
    return error

def func_middleware_body_limit(*, scope: dict, receive: Any, config_request_body_max_kb: int, config_request_form_max_kb: int) -> Any:
    """Wrap receive so a request body over its limit is refused with 413 before it fills memory: config_request_form_max_kb for multipart uploads (files go to disk past 1 MB), config_request_body_max_kb for everything else (JSON is held in memory, and parsing it takes several times its size). A declared Content-Length over the limit is refused before any of the body is read; a body without one is counted as it arrives."""
    headers = dict(scope.get("headers") or [])
    limit = (config_request_form_max_kb if headers.get(b"content-type", b"").startswith(b"multipart/form-data") else config_request_body_max_kb) * 1024
    try: declared = int(headers.get(b"content-length", b"0"))
    except ValueError: declared = 0
    received = 0
    async def receive_limited():
        nonlocal received
        if declared > limit: raise func_api_error(message=f"request body too large, limit {limit // 1024} KB", status_code=413)
        message = await receive()
        if message["type"] == "http.request":
            received += len(message.get("body", b""))
            if received > limit: raise func_api_error(message=f"request body too large, limit {limit // 1024} KB", status_code=413)
        return message
    return receive_limited

async def func_middleware_check_active(*, is_active: bool = True) -> None:
    """Check whether current API endpoint is active/enabled."""
    if not is_active: raise func_api_error(message="API endpoint is disabled", status_code=404)
    return

async def func_middleware_check_token(*, user_dict: dict, url_path: str, is_token: bool = False, user_check_role: list = None, user_check_deactivated: list = None, user_check_deleted: list = None) -> None:
    """Check whether current API requires token-authenticated user."""
    is_token_required = is_token or bool(user_check_role) or bool(user_check_deactivated) or bool(user_check_deleted)
    if is_token_required:
        if not user_dict: raise func_api_error(message="authorization token missing", status_code=401)
        token_type = user_dict.get("_token_type") if isinstance(user_dict, dict) else None
        if url_path == "/my/token-refresh":
            if token_type != "refresh": raise func_api_error(message="refresh token required", status_code=401)  # noqa: S105 - token kind, not a secret
        elif token_type != "access":  # noqa: S105 - token kind, not a secret
            raise func_api_error(message="access token required", status_code=401)
    return

def func_middleware_user_row_reader(*, client_postgres: asyncpg.Pool | None, user_dict: dict) -> Any:
    """One users-row read per request, shared by the role, deactivated and deleted checks: the first check that needs the database runs it, the others reuse the row."""
    row = {}
    async def read():
        if "value" not in row:
            if not client_postgres: raise func_api_error(message="postgres client missing", status_code=500)
            async with client_postgres.acquire() as conn:
                rows = await conn.fetch("select role, deactivated_at, deleted_at from users where id=$1", user_dict["id"])
            if not rows: raise func_api_error(message="user not found", status_code=401)
            row["value"] = rows[0]
        return row["value"]
    return read

async def func_middleware_check_user_deactivated(*, user_dict: dict, user_check_deactivated: Any, client_postgres: asyncpg.Pool | None, client_redis: Redis | None, cache_users_deactivated: dict, config_redis_cache_ttl_sec: int, user_row_read: Any = None) -> None:
    """Check if the user is deactivated using a strictly configured mode from config_api."""
    cfg = user_check_deactivated
    if not cfg or not user_dict: return
    mode = cfg.get("mode") if isinstance(cfg, dict) else (cfg[0] if isinstance(cfg, (list, tuple)) else None)
    if not mode: return
    async def fetch_deactivated_status(uid):
        if user_row_read: return (await user_row_read())["deactivated_at"]
        if not client_postgres: raise func_api_error(message="postgres client missing", status_code=500)
        async with client_postgres.acquire() as conn:
            rows = await conn.fetch("select id, deactivated_at from users where id=$1", uid)
        if not rows: raise func_api_error(message="user not found", status_code=401)
        return rows[0]["deactivated_at"]
    if mode == "redis":
        if not client_redis: raise func_api_error(message="redis client missing", status_code=500)
        cache_key = f"""cache:user:active:{user_dict["id"]}"""
        active_status = None
        cached_val = await client_redis.get(cache_key)
        if cached_val is not None:
            active_status = None if cached_val in (b"None", "None") else cached_val
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
        raise func_api_error(message=f"invalid mode: {mode}, allowed: redis, realtime, inmemory, token", status_code=500)
    if active_status == "absent": raise func_api_error(message="missing deactivated_at", status_code=500)
    if active_status is not None: raise func_api_error(message="user not active", status_code=403)

async def func_middleware_check_user_deleted(*, user_dict: dict, user_check_deleted: Any, client_postgres: asyncpg.Pool | None, client_redis: Redis | None, cache_users_deleted: dict, config_redis_cache_ttl_sec: int, user_row_read: Any = None) -> None:
    """Check if the user is deleted using a strictly configured mode from config_api."""
    cfg = user_check_deleted
    if not cfg or not user_dict: return
    mode = cfg.get("mode") if isinstance(cfg, dict) else (cfg[0] if isinstance(cfg, (list, tuple)) else None)
    if not mode: return
    async def fetch_deleted(uid):
        if user_row_read: return (await user_row_read())["deleted_at"]
        if not client_postgres: raise func_api_error(message="postgres client missing", status_code=500)
        async with client_postgres.acquire() as conn:
            rows = await conn.fetch("select deleted_at from users where id=$1", uid)
        if not rows: raise func_api_error(message="user not found", status_code=401)
        return rows[0]["deleted_at"]
    if mode == "redis":
        if not client_redis: raise func_api_error(message="redis client missing", status_code=500)
        cache_key = f"""cache:user:deleted_at:{user_dict["id"]}"""
        deleted_status = None
        cached_val = await client_redis.get(cache_key)
        if cached_val is not None:
            deleted_status = None if cached_val in (b"None", "None") else cached_val
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
        raise func_api_error(message=f"invalid mode: {mode}, allowed: redis, realtime, inmemory, token", status_code=500)
    if deleted_status == "absent": raise func_api_error(message="missing deleted_at", status_code=500)
    if deleted_status is not None: raise func_api_error(message="user is deleted", status_code=403)

async def func_middleware_check_role(*, user_dict: dict, user_check_role: Any, client_postgres: asyncpg.Pool | None, client_redis: Redis | None, cache_users_role: dict, config_redis_cache_ttl_sec: int, user_row_read: Any = None) -> None:
    """Ensure sufficient roles to access endpoints using a strictly configured mode from config_api."""
    cfg = user_check_role
    if not cfg: return
    if not user_dict: raise func_api_error(message="authorization token missing", status_code=401)
    if isinstance(cfg, dict):
        mode = cfg.get("mode")
        raw_roles = cfg.get("roles", [])
    elif isinstance(cfg, (list, tuple)):
        mode = cfg[0]
        raw_roles = cfg[1]
    else:
        return
    roles = {int(role) for role in raw_roles}
    async def fetch_role(uid):
        if user_row_read: return (await user_row_read())["role"]
        if not client_postgres: raise func_api_error(message="postgres client missing", status_code=500)
        async with client_postgres.acquire() as conn:
            rows = await conn.fetch("select role from users where id=$1", uid)
        if not rows: raise func_api_error(message="user not found", status_code=401)
        return rows[0]["role"]
    if mode == "redis":
        if not client_redis: raise func_api_error(message="redis client missing", status_code=500)
        cache_key = f"""cache:user:role:{user_dict["id"]}"""
        user_role = None
        cached_val = await client_redis.get(cache_key)
        if cached_val is not None:
            user_role = int(cached_val) if cached_val not in (b"", "") else None
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
        raise func_api_error(message=f"invalid mode: {mode}, allowed: redis, realtime, inmemory, token", status_code=500)
    if user_role == "absent": raise func_api_error(message="user role missing", status_code=500)
    if user_role is None or user_role == "": raise func_api_error(message="user role is null", status_code=403)
    if user_role == "role": raise func_api_error(message="user role is invalid", status_code=403)
    if not isinstance(user_role, int):
        try:
            user_role = int(user_role)
        except Exception:
            raise func_api_error(message="invalid user role type", status_code=403) from None
    if user_role not in roles: raise func_api_error(message="access denied", status_code=403)

async def func_middleware_check_ratelimiter(*, client_redis: Redis | None, rate_limit: Any = None, api_ratelimiting_times_sec: Any = None, url_path: str, identifier: str, cache_ratelimiter: dict) -> None:
    """Check and enforce API rate limits using either Redis or in-memory storage."""
    rl_config = rate_limit if rate_limit is not None else api_ratelimiting_times_sec
    if not rl_config: return
    if isinstance(rl_config, dict):
        mode = rl_config.get("mode")
        limit = rl_config.get("limit", 0)
        window = rl_config.get("window_sec", 0)
    elif isinstance(rl_config, (list, tuple)):
        mode, limit, window = rl_config
    else:
        return
    limit, window = int(limit), int(window)
    if limit <= 0 or window <= 0: return
    cache_key = f"ratelimiter:{url_path}:{identifier}"
    if mode == "redis":
        if not client_redis: raise func_api_error(message="redis client missing", status_code=500)
        # one atomic round trip: count the request and give a new (or expiry-less) key its window
        current_count = await client_redis.eval("local count = redis.call('INCR', KEYS[1]) if count == 1 or redis.call('TTL', KEYS[1]) == -1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end return count", 1, cache_key, window)
        if int(current_count) > limit: raise func_api_error(message="ratelimiter exceeded", status_code=429)
    elif mode == "inmemory":
        now = time.time()
        item = cache_ratelimiter.get(cache_key)
        if item and item["expire_at"] > now:
            if item["count"] + 1 > limit:
                raise func_api_error(message="ratelimiter exceeded", status_code=429)
            item["count"] += 1
        else:
            cache_ratelimiter[cache_key] = {"count": 1, "expire_at": now + window}
    else:
        raise func_api_error(message=f"invalid ratelimiter mode: {mode}, allowed: redis, inmemory", status_code=500)
    return

def func_middleware_postgres_select(*, client_postgres_dict: dict, cache_postgres_schema_dict: dict, is_connection_param: bool, connection: str | None) -> tuple:
    """Pick the request's PostgreSQL pool and schema cache: master, or ?connection= on routes flagged is_connection_param."""
    if connection and not is_connection_param: raise func_api_error(message="connection not allowed on this route", status_code=400)
    name = connection or "master"
    if name not in client_postgres_dict and name != "master": raise func_api_error(message=f"connection '{name}' not found", status_code=404)
    return client_postgres_dict.get(name), cache_postgres_schema_dict.get(name, {})

async def func_middleware_api_cache(*, mode: str, path: str, query_params: dict, cache: Any = None, api_cache_sec: Any = None, client_redis: Redis | None = None, user_id: int = 0, cache_api_response: dict = None, cache_api_response_bytes: dict = None, response: Any = None, is_gzip_accepted: bool = False, config_api_cache_inmemory_max_kb: int = 102400) -> Any:
    """Get or set middleware API cache for a request. Bodies are stored gzipped; a hit is sent still gzipped when the client accepts gzip (no decompress, fewer bytes). The inmemory cache holds at most config_api_cache_inmemory_max_kb of stored bodies per worker: over it, the oldest entries are dropped (they are read from the route again on their next request). cache_api_response_bytes ({"total": n}) keeps the stored size, so a set does not re-add every entry; without it the size is counted."""
    if mode not in ("get", "set"): raise func_api_error(message=f"invalid cache operation: {mode}, allowed: get, set", status_code=500)
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
    key = f"cache:api:{path}?{urlencode(sorted(query_params.items()))}:{uid}"    # encoded, so a value holding & or = cannot match another query
    if mode == "get":
        data = await client_redis.get(key) if cache_mode == "redis" else (item["data"] if (item := cache_api_response.get(key)) and item["expire_at"] > time.time() else None)
        if not data: return None
        if is_gzip_accepted: return Response(content=data, status_code=200, media_type="application/json", headers={"x-cache": "hit", "content-encoding": "gzip"})
        return Response(content=gzip.decompress(data), status_code=200, media_type="application/json", headers={"x-cache": "hit"})
    body = getattr(response, "body", None) or b"".join([chunk async for chunk in response.body_iterator])
    comp = gzip.compress(body, compresslevel=1)    # stored as raw bytes: level 1 is several times faster than the default 9 for JSON of this size
    if cache_mode == "redis": await client_redis.setex(key, ttl, comp)
    else:
        size = cache_api_response_bytes if cache_api_response_bytes is not None else {"total": sum(len(item["data"]) for item in cache_api_response.values())}
        if (old := cache_api_response.pop(key, None)): size["total"] -= len(old["data"])    # a re-set entry counts as the newest
        cache_api_response[key] = {"data": comp, "expire_at": time.time() + ttl}
        size["total"] += len(comp)
        while size["total"] > config_api_cache_inmemory_max_kb * 1024: size["total"] -= len(cache_api_response.pop(next(iter(cache_api_response)))["data"])    # dicts keep insertion order: the first is the oldest
    response = Response(content=body, status_code=response.status_code, media_type=response.media_type, headers=dict(response.headers))
    response.is_cache_set = True
    return response

async def func_middleware_api_background(*, scope: dict, body_bytes: bytes) -> Any:
    """Run the route's endpoint in a background task and return 202 at once.

    The endpoint is called directly: this task outlives the request, so it cannot go through the app's normal call chain.
    The middleware runs before routing, so the route is matched here the way Starlette's router does.
    """
    route = next((r for r in scope["app"].state.func_app_route_list(app=scope["app"]) if isinstance(r, APIRoute) and r.matches(scope)[0] == Match.FULL), None)
    if route is None: raise func_api_error(message="is_background is not supported on this path", status_code=400)
    async def receive(): return {"type": "http.request", "body": body_bytes}
    async def task():
        request = Request(scope=scope, receive=receive)
        try:
            await route.endpoint(request=request)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            func_runtime_error_record(runtime_error_count=scope["app"].state.runtime_error_count, key="background_task", error=e)
        finally:
            await func_request_form_close(request=request)
    task_obj = asyncio.create_task(task())
    app = scope.get("app")
    task_set = getattr(getattr(app, "state", None), "runtime_background_tasks", None) if app else None
    if task_set is not None:
        task_set.add(task_obj)
        task_obj.add_done_callback(task_set.discard)
    resp = responses.JSONResponse(status_code=202, content={"status": 1, "message": "added in background"})
    return resp

def func_middleware_client_ip(*, request: Request) -> Any:
    """Real client IP: the last X-Forwarded-For entry when the connection comes from a private (proxy) address, else the connection IP."""
    connection_ip = request.client.host if request.client else None
    header = request.headers.get("x-forwarded-for")
    if not header or not connection_ip: return connection_ip
    try:
        if not (ipaddress.ip_address(connection_ip).is_private or ipaddress.ip_address(connection_ip).is_loopback): return connection_ip
    except ValueError:
        return connection_ip
    # The last entry is the one the proxy added; earlier entries are whatever the client sent.
    value = header.split(",")[-1].strip()
    if value.startswith("["): value = value[1:value.find("]")] if "]" in value else value[1:]
    elif value.count(":") == 1: value = value.split(":")[0]
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return connection_ip

def func_middleware_log_query_params(*, query_params: Any) -> str:
    """Keep routine query metadata while redacting credentials and opaque payloads."""
    items = query_params.multi_items() if hasattr(query_params, "multi_items") else parse_qsl(str(query_params), keep_blank_values=True)
    sensitive = re.compile(r"password|passwd|secret|token|authorization|credential|api.?key|access.?key|signature|(?:^|_)(?:otp|code|dsn|sql|url|urls|filter|payload|question|sig)(?:$|_)", re.IGNORECASE)
    return urlencode([(key, "[REDACTED]" if sensitive.search(key) else value) for key, value in items])


def _redact_error_message(message):
    message = re.sub(r"(\b[a-z][a-z0-9+.-]*://)[^/\s@]+@", r"\1[REDACTED]@", message, flags=re.IGNORECASE)
    message = re.sub(r"\bBearer\s+[^\s,;]+", "Bearer [REDACTED]", message, flags=re.IGNORECASE)
    return re.sub(r"((?:password|passwd|secret|token|api[_-]?key|access[_-]?key|sig)\s*[=:]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s&;,]+)", r"\1[REDACTED]", message, flags=re.IGNORECASE)


async def func_middleware_api_response_error(*, exception: Exception, is_traceback: bool, sentry_dsn: str, request_id: str | None = None) -> tuple:
    """Central API error handler: formats database, client, and system exceptions into a standard JSON response."""
    import botocore.exceptions
    # Plain Exception stays 400; func_api_error and known infrastructure failures get their real status.
    status_code = exception.status_code if isinstance(getattr(exception, "status_code", None), int) else 400
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
        error_msg, status_code = "database conflict deadlock detected", 409
    elif isinstance(exception, asyncpg.exceptions.SerializationError):
        error_msg, status_code = "database conflict serialization error", 409
    elif isinstance(exception, (asyncpg.exceptions.CannotConnectNowError, asyncpg.exceptions.TooManyConnectionsError, asyncpg.exceptions.ConnectionDoesNotExistError)):
        error_msg, status_code = "database unavailable", 503
    elif isinstance(exception, asyncpg.PostgresError):
        error_msg = "database request failed"
    elif isinstance(exception, (asyncpg.exceptions.InterfaceError, ConnectionError, asyncio.TimeoutError)):
        error_msg, status_code = "database unavailable", 503
    elif isinstance(exception, botocore.exceptions.ClientError):
        error_msg = f"""cloud service error: {exception.response.get("Error", {}).get("Code", "Unknown")}"""
    elif isinstance(exception, (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError)):
        error_msg, status_code = "cache service unavailable", 503
    elif isinstance(exception, redis.exceptions.RedisError):
        error_msg, status_code = "cache service error", 500
    elif isinstance(exception, jwt.exceptions.ExpiredSignatureError):
        error_msg, status_code = "authentication token expired", 401
    elif isinstance(exception, jwt.exceptions.InvalidSignatureError):
        error_msg, status_code = "authentication token signature invalid", 401
    elif isinstance(exception, jwt.exceptions.DecodeError):
        error_msg, status_code = "authentication token malformed", 401
    elif isinstance(exception, jwt.exceptions.PyJWTError):
        error_msg, status_code = "authentication token invalid", 401
    elif isinstance(exception, httpx.HTTPStatusError):
        error_msg, status_code = f"external api error: {exception.response.status_code}", 502
    elif isinstance(exception, httpx.RequestError):
        error_msg, status_code = "external service request failed", 502
    elif isinstance(exception, (AttributeError, TypeError, KeyError)):
        error_msg, status_code = "internal server error", 500
    else:
        error_msg = str(exception)
    error_msg = _redact_error_message(error_msg)
    # a full traceback only for server errors (5xx); a client error (4xx: bad token, invalid input) is one line
    if is_traceback and status_code >= 500: traceback.print_tb(exception.__traceback__)
    if is_traceback: print(f"{status_code} {type(exception).__name__}: {error_msg}" + (f" (request {request_id})" if request_id else ""), file=sys.stderr)
    if sentry_dsn:
        import sentry_sdk
        sentry_sdk.capture_exception(exception, tags={"request_id": request_id} if request_id else None)
    return error_msg, responses.JSONResponse(status_code=status_code, content={"status": 0, "message": error_msg})

LOG_DETAIL_SECRET = re.compile(r"password|passwd|secret|token|authorization|cookie|credential|api.?key|access.?key|signature|(?:^|[_-])(?:otp|sig)(?:$|[_-])", re.IGNORECASE)
LOG_DETAIL_JSON_FIELD = re.compile(r'("((?:[^"\\]|\\.)*)"\s*:\s*)("(?:[^"\\]|\\.)*"|-?\d[\d.eE+-]*)')

def func_middleware_log_detail_is_json(*, content_type: str) -> bool:
    """A JSON body by its Content-Type (RFC 9110 8.3): application/json (RFC 8259) or a +json type (RFC 6839)."""
    media_type = content_type.split(";")[0].strip().lower()
    return media_type == "application/json" or media_type.endswith("+json")

def func_middleware_log_detail_start(*, scope: dict, receive: Any, config_log_api_detail_max_kb: int) -> tuple:
    """For config_is_log_api_detail: wrap receive so a JSON request body is copied (up to config_log_api_detail_max_kb) as the route reads it; returns (receive, detail)."""
    headers = dict(scope.get("headers") or [])
    detail = {"max_bytes": config_log_api_detail_max_kb * 1024, "request_type": headers.get(b"content-type", b"").decode("latin-1"), "request": bytearray(), "request_size": 0, "response_type": "", "response": bytearray(), "response_size": 0, "is_response_json": False}
    is_request_json = func_middleware_log_detail_is_json(content_type=detail["request_type"])
    async def receive_copied():
        message = await receive()
        if message["type"] == "http.request":
            body = message.get("body", b"")
            detail["request_size"] += len(body)
            if is_request_json and len(detail["request"]) < detail["max_bytes"]: detail["request"] += body[:detail["max_bytes"] - len(detail["request"])]
        return message
    return receive_copied, detail

def func_middleware_log_detail_send(*, message: dict, detail: dict) -> None:
    """For config_is_log_api_detail: copy a JSON response body (up to the limit) as it is sent; other types (CSV exports, files) and already-compressed bodies are not copied."""
    if message["type"] == "http.response.start":
        headers = {key.lower(): value for key, value in message.get("headers", [])}
        detail["response_type"] = headers.get(b"content-type", b"").decode("latin-1")
        detail["is_response_json"] = func_middleware_log_detail_is_json(content_type=detail["response_type"]) and b"content-encoding" not in headers
    elif message["type"] == "http.response.body":
        body = message.get("body", b"")
        detail["response_size"] += len(body)
        if detail["is_response_json"] and len(detail["response"]) < detail["max_bytes"]: detail["response"] += body[:detail["max_bytes"] - len(detail["response"])]
    return

def func_middleware_log_detail_body(*, body: bytearray, size: int, content_type: str, is_json: bool, max_bytes: int) -> str | None:
    """One body for log_api: JSON as text with secret fields masked, cut at the limit with a note; any other type only named; None when empty."""
    if not size: return None
    if not is_json: return f"[skipped: {content_type.split(';')[0].strip() or 'no content-type'}, {size} bytes]"
    text = LOG_DETAIL_JSON_FIELD.sub(lambda m: f'{m.group(1)}"[REDACTED]"' if LOG_DETAIL_SECRET.search(m.group(2)) else m.group(0), bytes(body).decode("utf-8", errors="replace"))
    return text if size <= max_bytes else f"{text}…[cut at {max_bytes // 1024} KB of {size} bytes]"

def func_middleware_log_detail_row(*, request: Request, detail: dict) -> dict:
    """The detail columns of one log_api row: the full query string and request headers (only secrets masked), the request and response bodies."""
    query_param = urlencode([(key, "[REDACTED]" if LOG_DETAIL_SECRET.search(key) else value) for key, value in request.query_params.multi_items()])
    header = {}
    for key, value in request.headers.items(): header[key] = "[REDACTED]" if LOG_DETAIL_SECRET.search(key) else (f"{header[key]}, {value}" if key in header else value)
    return {"query_param": query_param, "request_header": header, "request_body": func_middleware_log_detail_body(body=detail["request"], size=detail["request_size"], content_type=detail["request_type"], is_json=func_middleware_log_detail_is_json(content_type=detail["request_type"]), max_bytes=detail["max_bytes"]), "response_body": func_middleware_log_detail_body(body=detail["response"], size=detail["response_size"], content_type=detail["response_type"], is_json=detail["is_response_json"], max_bytes=detail["max_bytes"])}

def func_middleware_api_template_read(*, config_api: dict) -> list:
    """config_api routes with path parameters (/page/{name}) as (compiled pattern, route), built once at startup for func_middleware_api_config."""
    return [(compile_path(route)[0], route) for route in config_api if "{" in route]

def func_middleware_api_config(*, config_api: dict, path: str, cache_config_api_template: list) -> dict:
    """This request's config_api entry: the exact path first (one dict lookup), else the first route with path parameters that matches (/page/admin → /page/{name}), else {} (not a route)."""
    api_cfg = config_api.get(path)
    if api_cfg is not None: return api_cfg
    for pattern, route in cache_config_api_template:
        if pattern.match(path): return config_api[route]
    return {}

async def func_middleware_log_api_write(*, app_state: Any, request: Request, response_type: str, status_code: int | None, start: float, error: str | None, detail: dict | None = None) -> None:
    """Buffer one log_api row for a finished request; skipped when read-only or no log_api database, and write errors are counted, never raised."""
    if app_state.config_is_read_only or not getattr(app_state, "client_postgres_log_api", None): return
    try: await app_state.func_postgres_create(client_postgres=app_state.client_postgres_log_api, client_postgres_conn=None, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=app_state.cache_postgres_schema_dict.get(app_state.config_postgres_db_log_api, {}), buffer_postgres=app_state.buffer_postgres_log_api, buffer_rows_max=app_state.config_buffer_rows_max, buffer_full_mode="drop_oldest", runtime_error_count=app_state.runtime_error_count, is_trusted=True, config_column_regex=app_state.config_column_regex, buffer_limit=app_state.config_table.get("log_api", {}).get("buffer_limit", app_state.config_buffer_limit_default), mode="buffer", table="log_api", obj_list=[{"created_by_id": request.state.user.get("id") if getattr(request.state, "user", None) else None, "response_type": response_type, "ip_address": func_middleware_client_ip(request=request), "path": request.scope["path"], "method": request.method, "query_param": func_middleware_log_query_params(query_params=request.query_params), "status_code": status_code, "response_time_ms": int((time.perf_counter() - start) * 1000), "error": error, "request_id": getattr(request.state, "request_id", None)} | (func_middleware_log_detail_row(request=request, detail=detail) if detail is not None else {})])
    except Exception as e: func_runtime_error_record(runtime_error_count=app_state.runtime_error_count, key="log_api_write", error=e, print_every=100)
    return

def func_middleware_request_id(*, headers: Any) -> str:
    """This request's id: the caller's or proxy's x-request-id when it is a plain token (8-64 letters, digits, . _ -), else a new random one. Sent back as x-request-id, written to log_api and printed with errors, so a reported failure leads to its log row."""
    incoming = headers.get("x-request-id", "")
    return incoming if re.fullmatch(r"[A-Za-z0-9._-]{8,64}", incoming) else secrets.token_hex(8)

def func_middleware_security_headers(*, headers: list) -> list:
    """Return ASGI response headers with the baseline security headers added, keeping any the route already set."""
    present = {key.lower() for key, _ in headers}
    return list(headers) + [(key, value) for key, value in ((b"x-content-type-options", b"nosniff"), (b"x-frame-options", b"DENY"), (b"referrer-policy", b"strict-origin-when-cross-origin"), (b"x-xss-protection", b"0")) if key not in present]
