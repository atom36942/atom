"""Atom configuration checks."""

import re
from fastapi import FastAPI
from starlette.datastructures import State
from .app import func_app_route_list

def func_check_log_api_table(*, app_state: State) -> None:
    """Stop startup when API logging is on but the log database has no log_api table (rows would be dropped silently)."""
    log_db = app_state.config_postgres_db_log_api
    if app_state.config_is_read_only or log_db not in app_state.client_postgres_dict: return None
    if "log_api" not in app_state.cache_postgres_schema_dict.get(log_db, {}): raise Exception(f"config_postgres_db_log_api '{log_db}' has no log_api table")
    return None

def func_check_database_config(*, app_state: State) -> None:
    """Validate database pool sizing and named PostgreSQL connections."""
    def int_check(value, key):
        if isinstance(value, bool): raise Exception(f"invalid {key}: expected integer")
        try: value = int(value)
        except Exception: raise Exception(f"invalid {key}: expected integer") from None
        if value < 1: raise Exception(f"invalid {key}: minimum 1")
        return value
    pool_min = int_check(getattr(app_state, "config_postgres_pool_min_size", None), "config_postgres_pool_min_size")
    pool_max = int_check(getattr(app_state, "config_postgres_pool_max_size", None), "config_postgres_pool_max_size")
    if pool_max < pool_min: raise Exception("config_postgres_pool_max_size must be greater than or equal to config_postgres_pool_min_size")
    if getattr(app_state, "config_postgres_url", None) is not None: raise Exception("config_postgres_url was renamed to config_postgres_url_master")
    url_dict_value = getattr(app_state, "config_postgres_url_dict", None)
    if url_dict_value is not None and not isinstance(url_dict_value, dict): raise Exception("config_postgres_url_dict must be dict or None")
    url_dict = url_dict_value or {}
    for name, url in url_dict.items():
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name): raise Exception(f"invalid config_postgres_url_dict name: {name}")
        if not isinstance(url, str) or not url.strip().lower().startswith(("postgres://", "postgresql://")): raise Exception(f"invalid PostgreSQL URL for config_postgres_url_dict '{name}'")
    if url_dict and "master" not in url_dict: raise Exception("config_postgres_url_master is required: master is the default database")
    log_db = getattr(app_state, "config_postgres_db_log_api", None)
    if url_dict and log_db is not None and log_db not in url_dict: raise Exception(f"config_postgres_db_log_api '{log_db}' not found in config_postgres_url_dict")
    return None

def func_check_runtime_config(*, app_state: State) -> None:
    """Validate query limits, buffer bounds, and background-task intervals."""
    def int_check(value, key):
        if isinstance(value, bool): raise Exception(f"invalid {key}: expected integer")
        try: value = int(value)
        except Exception: raise Exception(f"invalid {key}: expected integer") from None
        if value < 1: raise Exception(f"invalid {key}: minimum 1")
        return value
    values = {key: int_check(getattr(app_state, key, None), key) for key in ("config_query_runner_read_limit", "config_query_runner_export_limit", "config_sql_read_limit_default", "config_sql_read_limit_max", "config_sql_read_relation_fetch_limit_max", "config_postgres_buffer_flush_auto_sec", "config_inmemory_cache_cleanup_auto_sec", "config_uvicorn_workers")}
    if values["config_sql_read_limit_default"] > values["config_sql_read_limit_max"]: raise Exception("config_sql_read_limit_default must not exceed config_sql_read_limit_max")
    for key in ("config_otp_retention_day", "config_log_api_retention_day"):
        retention = getattr(app_state, key, None)
        if retention is None: continue
        if isinstance(retention, bool) or not isinstance(retention, int) or not 1 <= retention <= 36500:
            raise ValueError(f"{key} must be an integer from 1 to 36500, or None")
        if key == "config_otp_retention_day" and retention * 86400 <= app_state.config_otp_expiry_sec:
            raise ValueError("config_otp_retention_day must exceed the OTP expiry window")
    buffer_limit = getattr(app_state, "config_buffer_limit_default", None)
    if buffer_limit is not None and (isinstance(buffer_limit, bool) or not isinstance(buffer_limit, int) or buffer_limit < 10 or buffer_limit > 5000): raise Exception("config_buffer_limit_default must be an integer between 10 and 5000")
    buffer_rows_max = getattr(app_state, "config_buffer_rows_max", None)
    if buffer_rows_max is not None and (isinstance(buffer_rows_max, bool) or not isinstance(buffer_rows_max, int) or buffer_rows_max < 1000): raise Exception("config_buffer_rows_max must be an integer of at least 1000")
    secret = getattr(app_state, "config_token_secret_key", None)
    if getattr(app_state, "config_is_prod", True) is not False and secret not in (None, "") and len(str(secret).encode()) < 32:
        raise Exception("config_token_secret_key must be at least 32 bytes in production (a short key lets tokens be forged); generate one with: python3 -c \"import secrets; print(secrets.token_urlsafe(48))\"")
    return None

def func_check_api_config(*, app: FastAPI) -> None:
    """Validate registered API middleware configuration and its Redis dependencies."""
    config_api = getattr(app.state, "config_api", {})
    if not isinstance(config_api, dict): raise Exception("config_api must be dict")
    route_paths = {route.path for route in func_app_route_list(app=app) if hasattr(route, "path")}
    api_ids = []
    user_mode_allowed = ("redis", "realtime", "inmemory", "token")
    api_mode_allowed = ("redis", "inmemory")
    api_keys_allowed = ("id", "is_active", "is_token", "is_postgres_param", "user_check_role", "user_check_deactivated", "user_check_deleted", "cache", "rate_limit", "api_cache_sec", "api_ratelimiting_times_sec")
    def flag_check(value, key):
        if not isinstance(value, bool): raise Exception(f"invalid {key}: expected bool")
    def int_check(value, key, min_value=0):
        if isinstance(value, bool): raise Exception(f"invalid {key}: expected integer")
        try: value = int(value)
        except Exception: raise Exception(f"invalid {key}: expected integer") from None
        if value < min_value: raise Exception(f"invalid {key}: minimum {min_value}")
        return value
    requires_redis = False
    requires_redis_user_state = False
    requires_redis_ratelimiter = False
    inmemory_list = []
    for path, cfg in config_api.items():
        if not isinstance(path, str) or not path.startswith("/"): raise Exception(f"invalid config_api path: {path}")
        if path not in route_paths: raise Exception(f"unused configuration in config_api: {path} (route not found)")
        if not isinstance(cfg, dict): raise Exception(f"{path} config must be dict")
        for key in cfg.keys():
            if key not in api_keys_allowed: raise Exception(f"{path} invalid config key: {key}")
        if "id" not in cfg: raise Exception(f"{path} missing required key: id")
        api_id = int_check(cfg["id"], f"{path} id", 1)
        if api_id in api_ids: raise Exception(f"duplicate api id: {api_id}")
        api_ids.append(api_id)
        if "is_active" in cfg: flag_check(cfg["is_active"], f"{path} is_active")
        if "is_postgres_param" in cfg: flag_check(cfg["is_postgres_param"], f"{path} is_postgres_param")
        if "is_token" not in cfg: raise Exception(f"{path} missing required key: is_token")
        flag_check(cfg["is_token"], f"{path} is_token")
        role_val = cfg.get("user_check_role")
        if role_val:
            if isinstance(role_val, dict):
                mode = role_val.get("mode")
                roles = role_val.get("roles")
            elif isinstance(role_val, (list, tuple)):
                mode = role_val[0] if len(role_val) > 0 else None
                roles = role_val[1] if len(role_val) > 1 else []
            else:
                raise Exception(f"{path} invalid user_check_role format")
            if mode not in user_mode_allowed: raise Exception(f"{path} invalid user_check_role mode: {mode}")
            if not isinstance(roles, list) or not roles: raise Exception(f"{path} invalid user_check_role roles")
            for role in roles: int_check(role, f"{path} user_check_role role", 1)
            if mode == "redis": requires_redis_user_state = True
            if mode == "inmemory": inmemory_list.append(f"{path} user_check_role")
        for key in ("user_check_deactivated", "user_check_deleted"):
            u_val = cfg.get(key)
            if u_val:
                mode = u_val.get("mode") if isinstance(u_val, dict) else (u_val[0] if isinstance(u_val, (list, tuple)) else None)
                if mode not in user_mode_allowed: raise Exception(f"{path} invalid {key} mode: {mode}")
                if mode == "redis": requires_redis_user_state = True
                if mode == "inmemory": inmemory_list.append(f"{path} {key}")
        c_val = cfg.get("cache") if "cache" in cfg else cfg.get("api_cache_sec")
        if c_val:
            if isinstance(c_val, dict):
                mode = c_val.get("mode")
                ttl = c_val.get("ttl_sec", 0)
                is_per_user = c_val.get("is_per_user", c_val.get("is_user_cache", False))
            elif isinstance(c_val, (list, tuple)):
                mode = c_val[0] if len(c_val) > 0 else None
                ttl = c_val[1] if len(c_val) > 1 else 0
                is_per_user = c_val[2] if len(c_val) > 2 else False
            else:
                raise Exception(f"{path} invalid cache format")
            if mode not in api_mode_allowed: raise Exception(f"{path} invalid cache mode: {mode}")
            ttl = int_check(ttl, f"{path} cache ttl", 1)
            if ttl > 315360000: raise Exception(f"{path} cache ttl exceeds 10 years")
            flag_check(is_per_user, f"{path} cache is_per_user flag")
            if mode == "redis": requires_redis = True
            if mode == "inmemory": inmemory_list.append(f"{path} cache")
        r_val = cfg.get("rate_limit") if "rate_limit" in cfg else cfg.get("api_ratelimiting_times_sec")
        if r_val:
            if isinstance(r_val, dict):
                mode = r_val.get("mode")
                limit = r_val.get("limit", 0)
                window = r_val.get("window_sec", 0)
            elif isinstance(r_val, (list, tuple)):
                mode = r_val[0] if len(r_val) > 0 else None
                limit = r_val[1] if len(r_val) > 1 else 0
                window = r_val[2] if len(r_val) > 2 else 0
            else:
                raise Exception(f"{path} invalid rate_limit format")
            if mode not in api_mode_allowed: raise Exception(f"{path} invalid rate_limit mode: {mode}")
            int_check(limit, f"{path} rate_limit limit", 1)
            window = int_check(window, f"{path} rate_limit window", 1)
            if window > 31536000: raise Exception(f"{path} rate_limit window exceeds 1 year")
            if mode == "redis": requires_redis_ratelimiter = True
            if mode == "inmemory": inmemory_list.append(f"{path} rate_limit")
    for path in route_paths:
        if path not in config_api:
            raise Exception(f"CRITICAL: Route '{path}' is missing from config_api. All routes must be explicitly configured.")
    if getattr(app.state, "config_redis_url", None) is not None: raise Exception("config_redis_url was renamed to config_redis_url_api_response")
    if requires_redis and not getattr(app.state, "config_redis_url_api_response", None):
        raise Exception("config_api uses redis cache mode but config_redis_url_api_response is missing")
    if requires_redis_user_state and not getattr(app.state, "config_redis_url_user_state", None):
        raise Exception("config_api uses redis user state check but config_redis_url_user_state is missing")
    if requires_redis_ratelimiter and not getattr(app.state, "config_redis_url_ratelimiter", None):
        raise Exception("config_api uses redis rate limiting but config_redis_url_ratelimiter is missing")
    redis_urls_required = []
    if requires_redis: redis_urls_required.append("config_redis_url_api_response")
    if requires_redis_user_state: redis_urls_required.append("config_redis_url_user_state")
    if requires_redis_ratelimiter: redis_urls_required.append("config_redis_url_ratelimiter")
    for key in redis_urls_required:
        url = getattr(app.state, key, None)
        if not isinstance(url, str) or not url.strip().lower().startswith(("redis://", "rediss://", "unix://")):
            raise Exception(f"{key} must be a valid Redis URL")
    workers = int(getattr(app.state, "config_uvicorn_workers", 1) or 1)
    if workers > 1 and inmemory_list:
        raise Exception(f"config_uvicorn_workers={workers} needs state shared across workers; inmemory is per worker. Switch these to redis (user checks may also use realtime or token): {', '.join(inmemory_list)}")
    return None

async def func_check_postgres_connections(*, app_state: State, client_postgres_dict: dict) -> None:
    """Warn when every worker's pools together could exceed a Postgres server's max_connections."""
    workers = int(getattr(app_state, "config_uvicorn_workers", 1) or 1)
    pool_max = int(getattr(app_state, "config_postgres_pool_max_size", 0) or 0)
    for name, pool in client_postgres_dict.items():
        if pool is None: continue
        try:
            async with pool.acquire(timeout=5) as conn:
                max_connections = int(await conn.fetchval("SHOW max_connections", timeout=5))
                reserved = int(await conn.fetchval("SHOW superuser_reserved_connections", timeout=5))
        except Exception as e:
            print(f"⚠️ postgres {name}: connection limit check skipped: {e}")
            continue
        needed = workers * pool_max * len(client_postgres_dict)
        if needed > max_connections - reserved:
            print(f"⚠️ postgres {name}: {workers} workers x {pool_max} pool max x {len(client_postgres_dict)} pools = up to {needed} connections, above max_connections {max_connections} minus {reserved} reserved; lower config_postgres_pool_max_size or config_uvicorn_workers")
    return None

def func_check(*, app: FastAPI) -> None:
    """Validate database, runtime, and API configuration before client initialization."""
    func_check_database_config(app_state=app.state)
    func_check_runtime_config(app_state=app.state)
    func_check_api_config(app=app)
    return None
