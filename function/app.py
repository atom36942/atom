async def func_check_ratelimiter(client_redis_ratelimiter: any, config_api: dict, path: str, identity: str) -> None:
    """Enforce API ratelimiting using Redis, tracking hits within a rolling time window if configured for the route."""
    if not client_redis_ratelimiter:
         return None
    api_cfg = config_api.get(path)
    if not api_cfg:
        return None
    limit_cfg = api_cfg.get("api_ratelimiting_times_sec")
    if not limit_cfg:
        return None
    tech, limit, window = limit_cfg
    if tech != "inmemory" and tech != "realtime":
        raise Exception(f"invalid ratelimiting tech {tech}")
    cache_key = f"ratelimit:{path}:{identity}"
    if tech == "inmemory":
        if not hasattr(func_check_ratelimiter, "cache"):
            func_check_ratelimiter.cache = {}
        import time
        now = time.time()
        hits, expire_at = func_check_ratelimiter.cache.get(cache_key, (0, now + window))
        if now > expire_at:
            hits, expire_at = 0, now + window
        hits += 1
        func_check_ratelimiter.cache[cache_key] = (hits, expire_at)
        if hits > limit:
            raise Exception("ratelimit exceeded (in-memory)")
    else:
        pipeline = client_redis_ratelimiter.pipeline()
        pipeline.incr(cache_key)
        pipeline.expire(cache_key, window)
        results = await pipeline.execute()
        if results[0] > limit:
            raise Exception("ratelimit exceeded (redis)")

async def func_check_is_active(user_obj: dict, request_path: str, config_api: dict, client_postgres_pool: any, client_redis: any, cache_users_is_active: dict, config_redis_cache_ttl_sec: int) -> None:
    """Verify that the user account is active, optionally using cached state or querying the database in realtime."""
    if not user_obj:
        return None
    api_cfg = config_api.get(request_path)
    if not api_cfg:
        return None
    check_cfg = api_cfg.get("user_is_active_check")
    if not check_cfg:
        return None
    tech, _ = check_cfg
    user_id = user_obj.get("id")
    is_active = None
    if tech == "inmemory":
        is_active = cache_users_is_active.get(user_id)
    elif tech == "token":
        is_active = user_obj.get("is_active")
    elif tech == "realtime":
        async with client_postgres_pool.acquire() as conn:
            is_active = await conn.fetchval("SELECT is_active FROM users WHERE id=$1", user_id)
    if is_active != 1:
        raise Exception("user account is inactive")

async def func_check_admin(user_obj: dict, request_path: str, config_api: dict, client_postgres_pool: any, client_redis: any, cache_users_role: dict, config_redis_cache_ttl_sec: int) -> None:
    """Validate that the user has the required roles for an administrative endpoint, supporting multi-tier role checks."""
    if not user_obj:
        return None
    api_cfg = config_api.get(request_path)
    if not api_cfg:
        return None
    check_cfg = api_cfg.get("user_role_check")
    if not check_cfg:
        return None
    tech, allowed_roles = check_cfg
    user_id = user_obj.get("id")
    user_role = None
    if tech == "inmemory":
        user_role = cache_users_role.get(user_id)
    elif tech == "token":
        user_role = user_obj.get("role")
    elif tech == "realtime":
        async with client_postgres_pool.acquire() as conn:
            user_role = await conn.fetchval("SELECT role FROM users WHERE id=$1", user_id)
    if user_role not in allowed_roles:
        raise Exception(f"unauthorized role: {user_role}, allowed: {allowed_roles}")

async def func_check_cache(mode: str, path: str, query_params: dict, config_api: dict, client_redis: any, user_id: int, response: any) -> any:
    """Middleware-level cache handler: fetches or stores JSON responses in Redis using a compound key of path, user, and query parameters."""
    if not client_redis:
        return None
    import orjson
    from fastapi import responses
    cache_cfg = config_api.get(path, {}).get("api_cache_sec")
    if not cache_cfg:
        return None
    tech, ttl = cache_cfg
    cache_key = f"api_cache:{path}:{user_id}:{orjson.dumps(query_params).decode('utf-8')}"
    if mode == "get":
        cached_data = await client_redis.get(cache_key)
        if cached_data:
            return responses.JSONResponse(content=orjson.loads(cached_data))
    elif mode == "set":
        await client_redis.set(cache_key, orjson.dumps(response.body).decode('utf-8'), ex=ttl)
        return response
    return None

def func_fastapi_app_read(lifespan_handler: any, is_debug_mode: int) -> any:
    """Initialize a FastAPI application with debug mode and lifespan handler, disabling default OpenAPI routes."""
    from fastapi import FastAPI
    return FastAPI(debug=bool(is_debug_mode), lifespan=lifespan_handler, openapi_url=None, docs_url=None, redoc_url=None)

def func_app_add_cors(fastapi_app: any, origins: list, methods: list, headers: list, is_allow_credentials: int) -> None:
    """Add CORS middleware to the FastAPI application."""
    from fastapi.middleware.cors import CORSMiddleware
    fastapi_app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=methods, allow_headers=headers, allow_credentials=bool(is_allow_credentials))

def func_app_add_prometheus(fastapi_app: any) -> None:
    """Expose Prometheus metrics for the FastAPI application."""
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(fastapi_app).expose(fastapi_app)

def func_app_state_add(fastapi_app: any, config_dict: dict, prefix: str) -> None:
    """Inject configuration values into the FastAPI application state based on a prefix."""
    for key, val in config_dict.items():
        if key.startswith(prefix):
            setattr(fastapi_app.state, key, val)

def func_app_add_sentry(sentry_dsn: str) -> None:
    """Initialize Sentry SDK for error tracking and profiling."""
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    sentry_sdk.init(dsn=sentry_dsn, integrations=[FastApiIntegration()], traces_sample_rate=1.0, profiles_sample_rate=1.0, send_default_pii=True)

def func_app_add_static(fastapi_app: any, folder_path: str, mount_path: str) -> None:
    """Mount a static directory to the FastAPI application."""
    from fastapi.staticfiles import StaticFiles
    fastapi_app.mount(mount_path, StaticFiles(directory=folder_path), name="static")

def func_add_router(fastapi_app: any) -> None:
    """Dynamically discover and include all FastAPI routers from the router directory."""
    import sys, importlib.util, traceback
    from pathlib import Path
    root_dir = Path("./router").resolve()
    if not root_dir.exists():
        return None
    for py_file in root_dir.rglob("*.py"):
        if py_file.name.startswith((".", "__")):
            continue
        try:
            rel_path = py_file.relative_to(root_dir)
            module_name = "router." + ".".join(rel_path.with_suffix("").parts)
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                fastapi_app.include_router(getattr(module, "router"))
        except Exception:
            traceback.print_exc()
