"""Atom config functions."""

def func_check_database_config(*, app_state: any) -> None:
    """Validate database pool sizing and named PostgreSQL connections."""
    import re
    def int_check(value, key):
        if isinstance(value, bool): raise Exception(f"invalid {key}: expected integer")
        try: value = int(value)
        except Exception: raise Exception(f"invalid {key}: expected integer")
        if value < 1: raise Exception(f"invalid {key}: minimum 1")
        return value
    pool_min = int_check(getattr(app_state, "config_postgres_pool_min_size", None), "config_postgres_pool_min_size")
    pool_max = int_check(getattr(app_state, "config_postgres_pool_max_size", None), "config_postgres_pool_max_size")
    if pool_max < pool_min: raise Exception("config_postgres_pool_max_size must be greater than or equal to config_postgres_pool_min_size")
    url_dict_value = getattr(app_state, "config_postgres_url_dict", None)
    if url_dict_value is not None and not isinstance(url_dict_value, dict): raise Exception("config_postgres_url_dict must be dict or None")
    url_dict = url_dict_value or {}
    for name, url in url_dict.items():
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name): raise Exception(f"invalid config_postgres_url_dict name: {name}")
        if not isinstance(url, str) or not url.strip().lower().startswith(("postgres://", "postgresql://")): raise Exception(f"invalid PostgreSQL URL for config_postgres_url_dict '{name}'")
    log_db = getattr(app_state, "config_postgres_db_log_api", None)
    if log_db is not None and log_db not in url_dict: raise Exception(f"config_postgres_db_log_api '{log_db}' not found in config_postgres_url_dict")
    return None

def func_check_runtime_config(*, app_state: any) -> None:
    """Validate query limits, buffer bounds, and background-task intervals."""
    def int_check(value, key):
        if isinstance(value, bool): raise Exception(f"invalid {key}: expected integer")
        try: value = int(value)
        except Exception: raise Exception(f"invalid {key}: expected integer")
        if value < 1: raise Exception(f"invalid {key}: minimum 1")
        return value
    values = {key: int_check(getattr(app_state, key, None), key) for key in ("config_query_runner_read_limit", "config_query_runner_export_limit", "config_sql_read_limit_default", "config_sql_read_limit_max", "config_sql_read_relation_fetch_limit_max", "config_postgres_buffer_flush_auto_sec", "config_inmemory_cache_cleanup_auto_sec")}
    if values["config_sql_read_limit_default"] > values["config_sql_read_limit_max"]: raise Exception("config_sql_read_limit_default must not exceed config_sql_read_limit_max")
    buffer_limit = getattr(app_state, "config_buffer_limit_default", None)
    if buffer_limit is not None and (isinstance(buffer_limit, bool) or not isinstance(buffer_limit, int) or buffer_limit < 10 or buffer_limit > 5000): raise Exception("config_buffer_limit_default must be an integer between 10 and 5000")
    return None

def func_check_api_config(*, app: any) -> None:
    """Validate registered API middleware configuration and its Redis dependencies."""
    config_api = getattr(app.state, "config_api", {})
    if not isinstance(config_api, dict): raise Exception("config_api must be dict")
    route_paths = {route.path for route in app.routes if hasattr(route, "path")}
    api_ids = []
    user_mode_allowed = ("redis", "realtime", "inmemory", "token")
    api_mode_allowed = ("redis", "inmemory")
    api_keys_allowed = ("id", "is_active", "is_token", "user_check_role", "user_check_deactivated", "user_check_deleted", "cache", "rate_limit", "api_cache_sec", "api_ratelimiting_times_sec")
    def flag_check(value, key):
        if not isinstance(value, bool): raise Exception(f"invalid {key}: expected bool")
    def int_check(value, key, min_value=0):
        if isinstance(value, bool): raise Exception(f"invalid {key}: expected integer")
        try: value = int(value)
        except Exception: raise Exception(f"invalid {key}: expected integer")
        if value < min_value: raise Exception(f"invalid {key}: minimum {min_value}")
        return value
    requires_redis = False
    requires_redis_user_state = False
    requires_redis_ratelimiter = False
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
        for key in ("user_check_deactivated", "user_check_deleted"):
            u_val = cfg.get(key)
            if u_val:
                mode = u_val.get("mode") if isinstance(u_val, dict) else (u_val[0] if isinstance(u_val, (list, tuple)) else None)
                if mode not in user_mode_allowed: raise Exception(f"{path} invalid {key} mode: {mode}")
                if mode == "redis": requires_redis_user_state = True
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
    for path in route_paths:
        if path not in config_api:
            raise Exception(f"CRITICAL: Route '{path}' is missing from config_api. All routes must be explicitly configured.")
    if requires_redis and not getattr(app.state, "config_redis_url", None):
        raise Exception("config_api uses redis mode but config_redis_url is missing")
    if requires_redis_user_state and not getattr(app.state, "config_redis_url_user_state", None):
        raise Exception("config_api uses redis user state check but config_redis_url_user_state is missing")
    if requires_redis_ratelimiter and not getattr(app.state, "config_redis_url_ratelimiter", None):
        raise Exception("config_api uses redis rate limiting but config_redis_url_ratelimiter is missing")
    redis_urls_required = []
    if requires_redis: redis_urls_required.append("config_redis_url")
    if requires_redis_user_state: redis_urls_required.append("config_redis_url_user_state")
    if requires_redis_ratelimiter: redis_urls_required.append("config_redis_url_ratelimiter")
    for key in redis_urls_required:
        url = getattr(app.state, key, None)
        if not isinstance(url, str) or not url.strip().lower().startswith(("redis://", "rediss://", "unix://")):
            raise Exception(f"{key} must be a valid Redis URL")
    return None

def func_check(*, app: any) -> None:
    """Validate database, runtime, and API configuration before client initialization."""
    func_check_database_config(app_state=app.state)
    func_check_runtime_config(app_state=app.state)
    func_check_api_config(app=app)
    return None
