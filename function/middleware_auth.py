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
    if not cfg or not user_dict:
        return None
    mode, active_flag = cfg
    if active_flag == 0:
        return None
    async def fetch_is_active(uid):
        if not client_postgres_pool:
            raise Exception("postgres client missing")
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
        if not client_postgres_pool:
            raise Exception("postgres client missing")
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
