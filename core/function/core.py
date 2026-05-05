async def func_client_read_postgres(*, config_postgres: dict) -> any:
    """Initialize PostgreSQL connection pool and log status."""
    if not config_postgres.get("dsn"): return None
    import asyncpg
    return await asyncpg.create_pool(dsn=config_postgres["dsn"], min_size=config_postgres["min_size"], max_size=config_postgres["max_size"])

async def func_client_read_mongodb(*, config_mongodb_url: str) -> any:
    """Initialize MongoDB client and log status."""
    if not config_mongodb_url: return None
    import motor.motor_asyncio
    return motor.motor_asyncio.AsyncIOMotorClient(config_mongodb_url)

def func_client_read_gemini(*, config_gemini_key: str) -> any:
    """Initialize Gemini client and log status."""
    if not config_gemini_key: return None
    import google.generativeai as genai
    genai.configure(api_key=config_gemini_key)
    return genai

def func_client_read_openai(*, config_openai_key: str) -> any:
    """Initialize OpenAI client and log status."""
    if not config_openai_key: return None
    import openai
    return openai.OpenAI(api_key=config_openai_key)

def func_client_read_ses(*, config_aws_access_key_id: str, config_aws_secret_access_key: str, config_ses_region_name: str) -> any:
    """Initialize AWS SES client and log status."""
    if not config_ses_region_name: return None
    import boto3
    return boto3.client("ses", region_name=config_ses_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key)

def func_client_read_sns(*, config_aws_access_key_id: str, config_aws_secret_access_key: str, config_sns_region_name: str) -> any:
    """Initialize AWS SNS client and log status."""
    if not config_sns_region_name: return None
    import boto3
    return boto3.client("sns", region_name=config_sns_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_sns_region_name)

async def func_client_read_s3(*, config_aws_access_key_id: str, config_aws_secret_access_key: str, config_s3_region_name: str) -> any:
    """Initialize AWS S3 client and resource and log status."""
    if not config_s3_region_name: return None, None
    import aiobotocore.session, boto3
    client = aiobotocore.session.get_session().create_client("s3", region_name=config_s3_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key)
    resource = boto3.resource("s3", region_name=config_s3_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key)
    return client, resource

async def func_client_read_redis(*, config_redis_url: str, event_name: str = "🔴 redis client") -> any:
    """Initialize Redis client and log status."""
    if not config_redis_url: return None
    import redis.asyncio as redis
    return redis.Redis.from_pool(redis.ConnectionPool.from_url(config_redis_url))

def func_client_read_celery_producer(*, config_celery_broker_url: str, config_celery_backend_url: str) -> any:
    """Initialize Celery producer client and log status."""
    if not config_celery_broker_url: return None
    from celery import Celery
    return Celery("atom", broker=config_celery_broker_url, backend=config_celery_backend_url)

async def func_client_read_rabbitmq_producer(*, config_rabbitmq_url: str) -> any:
    """Initialize RabbitMQ producer connection and channel and log status."""
    if not config_rabbitmq_url: return None, None
    import aio_pika
    conn = await aio_pika.connect_robust(config_rabbitmq_url)
    channel = await conn.channel()
    return conn, channel

async def func_client_read_kafka_producer(*, config_kafka_url: str, config_kafka_username: str, config_kafka_password: str) -> any:
    """Initialize Kafka producer client and log status."""
    if not config_kafka_url: return None
    from aiokafka import AIOKafkaProducer
    p = AIOKafkaProducer(bootstrap_servers=config_kafka_url, security_protocol="SASL_SSL", sasl_mechanism="PLAIN", sasl_plain_username=config_kafka_username, sasl_plain_password=config_kafka_password) if config_kafka_username else AIOKafkaProducer(bootstrap_servers=config_kafka_url)
    await p.start()
    return p

def func_client_read_posthog(*, config_posthog_project_host: str, config_posthog_project_key: str) -> any:
    """Initialize PostHog client and log status."""
    if not config_posthog_project_key: return None
    from posthog import Posthog
    return Posthog(config_posthog_project_key, host=config_posthog_project_host)

async def func_client_read_sftp(*, config_sftp_host: str, config_sftp_port: int, config_sftp_username: str, config_sftp_password: str, config_sftp_key_path: str, config_sftp_auth_method: str) -> any:
    """Initialize SFTP connection and log status."""
    if not config_sftp_host: return None
    import asyncssh
    if config_sftp_auth_method not in ("key", "password"): raise Exception(f"invalid sftp auth mode: {config_sftp_auth_method}")
    if config_sftp_auth_method == "key":
        if not config_sftp_key_path: raise Exception("ssh key path missing")
        return await asyncssh.connect(host=config_sftp_host, port=int(config_sftp_port), username=config_sftp_username, client_keys=[config_sftp_key_path], known_hosts=None)
    else:
        if not config_sftp_password: raise Exception("password missing")
        return await asyncssh.connect(host=config_sftp_host, port=int(config_sftp_port), username=config_sftp_username, password=config_sftp_password, known_hosts=None)

async def func_client_read_azure_blob(*, config_azure_account_name: str, config_azure_account_key: str, config_azure_connection_string: str) -> any:
    """Initialize Azure Blob Service client (async) and log status."""
    if not config_azure_account_name and not config_azure_connection_string: return None
    from azure.storage.blob.aio import BlobServiceClient
    if config_azure_connection_string: return BlobServiceClient.from_connection_string(config_azure_connection_string)
    else: return BlobServiceClient(account_url=f"https://{config_azure_account_name}.blob.core.windows.net", credential=config_azure_account_key)

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

async def func_check_admin(*, user_dict: dict, url_path: str, config_api: dict, client_postgres_pool: any, client_redis: any, cache_users_role: dict, config_redis_cache_ttl_sec: int) -> None:
    """Ensure sufficient roles to access admin endpoints using a strictly configured mode from config_api."""
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
        pass
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

def func_structure_create(*, directories: list, files: list) -> None:
    """Ensure required directory structure and files exist on startup."""
    import os
    for directory in directories:
        if not os.path.exists(directory): os.makedirs(directory, exist_ok=True)
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

async def func_postgres_schema_read(*, client_postgres_pool: any) -> dict:
    """Read full PostgreSQL schema from public namespace, mapping internal data types to a standard dictionary format."""
    query = """
        SELECT table_name, column_name, data_type, is_nullable, column_default 
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        ORDER BY table_name, ordinal_position;
    """
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query)
    schema = {}
    for r in records:
        tbl = r["table_name"]
        if tbl not in schema: schema[tbl] = {}
        schema[tbl][r["column_name"]] = {"datatype": r["data_type"], "is_nullable": r["is_nullable"], "default": r["column_default"]}
    return schema

async def func_postgres_serialize(*, client_postgres_pool: any, client_password_hasher: any, cache_postgres_schema: dict, table: str, obj_list: list, is_base: int) -> list:
    """Format and validate a list of objects based on PostgreSQL schema, including password hashing, JSON encoding, and type casting."""
    import orjson, re
    from datetime import datetime
    schema = cache_postgres_schema.get(table, {})
    if not schema: return obj_list
    res_list = []
    for obj in obj_list:
        new_obj = {}
        for col, val in obj.items():
            if col not in schema: continue
            dtype = schema[col]["datatype"].lower()
            if val is None or str(val).lower() == "null":
                new_obj[col] = None
                continue
            if col == "password":
                new_obj[col] = client_password_hasher.hash(str(val))
            elif "json" in dtype:
                new_obj[col] = orjson.dumps(val).decode("utf-8") if not isinstance(val, str) else val
            elif "[]" in dtype or "array" in dtype:
                if isinstance(val, str):
                    new_obj[col] = [x.strip() for x in val.split(",")]
                else:
                    new_obj[col] = val
            elif "timestamp" in dtype:
                if isinstance(val, str):
                    try: new_obj[col] = datetime.fromisoformat(val.replace("Z", "+00:00"))
                    except: new_obj[col] = val
                else: new_obj[col] = val
            elif "int" in dtype or "serial" in dtype:
                new_obj[col] = int(val)
            elif "bool" in dtype:
                new_obj[col] = bool(val)
            elif "float" in dtype or "numeric" in dtype or "double" in dtype:
                new_obj[col] = float(val)
            else:
                new_obj[col] = str(val)
        if not is_base:
            if "created_at" in schema and "created_at" not in new_obj: new_obj["created_at"] = datetime.now()
            if "updated_at" in schema and "updated_at" not in new_obj: new_obj["updated_at"] = datetime.now()
        res_list.append(new_obj)
    return res_list

async def func_postgres_schema_init(*, client_postgres_pool: any, client_password_hasher: any, config_postgres: dict, config_postgres_root_user_password: str) -> str:
    """Initialize PostgreSQL schema from configuration, creating tables and the mandatory root user (id=1)."""
    async with client_postgres_pool.acquire() as conn:
        for table_name, cols in config_postgres.get("table", {}).items():
            col_defs = []
            for col in cols:
                d = f"{col['name']} {col['datatype']}"
                if col.get("is_primary"): d += " PRIMARY KEY"
                if not col.get("is_nullable"): d += " NOT NULL"
                if col.get("default") is not None: d += f" DEFAULT {col['default']}"
                if col.get("is_unique"): d += " UNIQUE"
                col_defs.append(d)
            await conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(col_defs)});")
        if config_postgres_root_user_password:
            res = await conn.fetchval("SELECT id FROM users WHERE id=1")
            if not res:
                hashed = client_password_hasher.hash(config_postgres_root_user_password)
                await conn.execute("INSERT INTO users (id, role, password, email, is_active) VALUES (1, 1, $1, 'root@atom.com', 1) ON CONFLICT DO NOTHING", hashed)
    return "schema initialized"

async def func_postgres_map_column(*, client_postgres_pool: any, config_sql: str) -> dict:
    """Execute a mapping SQL query and return a dictionary from the first two columns."""
    if not config_sql: return {}
    async with client_postgres_pool.acquire() as conn:
        rows = await conn.fetch(config_sql)
    return {r[0]: r[1] for r in rows}


