# import
import ipaddress
import re
import sys
from fastapi import FastAPI
from starlette.routing import WebSocketRoute
from starlette.datastructures import State
from .app import func_app_route_list
from .postgres_schema import CONTROL_ACCESS
from .postgres_schema import func_postgres_schema_config_validate
from .postgres_schema import func_postgres_schema_dict
from .postgres_schema import func_postgres_users_access
from .schedule import func_schedule_read
from .webhook import func_webhook_verify_scheme_check

# function
def func_check_log_api_table(*, app_state: State) -> None:
    """Stop startup when API logging is on but the log database has no log_api table (rows would be dropped silently)."""
    log_db = getattr(app_state, "cache_log_api_database", None)
    if not app_state.config_is_log_api or app_state.config_is_read_only or log_db not in app_state.client_postgres_dict: return
    if "log_api" not in app_state.cache_postgres_schema_dict.get(log_db, {}): raise Exception(f"database {log_db} has no log_api table (it is in config_postgres_schema_{log_db})")
    return

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
    for key, example in (("config_postgres_url", "master"), ("config_redis_url", "api_response"), ("config_clickhouse_url", "master"), ("config_mssql_url", "master")):
        if getattr(app_state, key, None) is not None: raise Exception(f"{key} needs a name suffix, e.g. {key}_{example}")
    url_dict_value = getattr(app_state, "config_postgres_url_dict", None)
    if url_dict_value is not None and not isinstance(url_dict_value, dict): raise Exception("config_postgres_url_dict must be dict or None")
    url_dict = url_dict_value or {}
    for name, url in url_dict.items():
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name): raise Exception(f"invalid config_postgres_url_dict name: {name}")
        if not isinstance(url, str) or not url.strip().lower().startswith(("postgres://", "postgresql://")): raise Exception(f"invalid PostgreSQL URL for config_postgres_url_dict '{name}'")
    if url_dict and "master" not in url_dict: raise Exception("config_postgres_url_master is required: master is the default database")
    for key in ("config_clickhouse_url_dict", "config_mssql_url_dict"):
        named_url_dict = getattr(app_state, key, None)
        if named_url_dict is not None and not isinstance(named_url_dict, dict): raise Exception(f"{key} must be dict or None")
        for name, url in (named_url_dict or {}).items():
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name): raise Exception(f"invalid {key} name: {name}")
            if url is not None and not isinstance(url, str): raise Exception(f"invalid URL for {key} '{name}'")
    # per-database pool sizes: config_<db>_pool_min_size_<name> / _max_size_<name> must name a database that has a URL, a typo would be silently ignored
    values = getattr(app_state, "_state", None) or vars(app_state)    # Starlette's State keeps its values in _state
    for db in ("postgres", "mssql"):
        names = set(getattr(app_state, f"config_{db}_url_dict", None) or {})
        for key in sorted(values):
            match = re.fullmatch(rf"config_{db}_pool_(min|max)_size_(\w+)", key)
            if not match: continue
            if match.group(2) not in names: raise Exception(f"{key}: no database named {match.group(2)} (config_{db}_url_{match.group(2)} is not set)")
            int_check(values[key], key)
        for name in names:
            if values.get(f"config_{db}_pool_min_size_{name}") is None and values.get(f"config_{db}_pool_max_size_{name}") is None: continue
            size_min, size_max = (int(values.get(f"config_{db}_pool_{size}_size_{name}") or values.get(f"config_{db}_pool_{size}_size")) for size in ("min", "max"))
            if size_max < size_min: raise Exception(f"config_{db}_pool_max_size_{name} ({size_max}) must be at least its min size ({size_min})")
    # per-database buffer flush interval: config_postgres_buffer_flush_auto_sec_<name> must name a database that has a URL
    for key in sorted(values):
        match = re.fullmatch(r"config_postgres_buffer_flush_auto_sec_(\w+)", key)
        if not match: continue
        if match.group(1) not in set(getattr(app_state, "config_postgres_url_dict", None) or {}): raise Exception(f"{key}: no database named {match.group(1)} (config_postgres_url_{match.group(1)} is not set)")
        int_check(values[key], key)
    return

def func_check_postgres_schema(*, app_state: State) -> None:
    """Stop startup on a wrong config_postgres_schema_<name>: master missing, a name without a database (config_postgres_url_<name>), an invalid table,
    or API logging on while log_api is in no schema, or in more than one (the database whose schema has it gets the API logs)."""
    values = getattr(app_state, "_state", None) or vars(app_state)
    schemas = func_postgres_schema_dict(values=values)
    if not isinstance(schemas.get("master"), dict): raise Exception("config_postgres_schema_master is required: Atom's tables live there")
    url_names = set(values.get("config_postgres_url_dict") or {})
    for name, schema in schemas.items():
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name): raise Exception(f"invalid config_postgres_schema_ name: {name!r}")
        if url_names and name not in url_names: raise Exception(f"config_postgres_schema_{name}: no database named {name} (config_postgres_url_{name} is not set)")
        try: func_postgres_schema_config_validate(config_postgres_schema=schema)
        except Exception as e: raise Exception(f"config_postgres_schema_{name}: {e}") from None
    if values.get("config_is_log_api", True):
        holders = [name for name, schema in schemas.items() if "log_api" in (schema.get("table") or {})]
        if not holders: raise Exception("config_is_log_api is on but no config_postgres_schema_<name> has log_api: keep it in master, or move it to the database for logs with its control entries (my_read, row_update_disabled, buffer_limit, retention_day): docs/database.md, Storing Logs in an Isolated Database")
        if len(holders) > 1: raise Exception(f"log_api is in config_postgres_schema_{holders[0]} and config_postgres_schema_{holders[1]}: keep it in one (that database gets the API logs)")
    return

def func_check_runtime_config(*, app_state: State) -> None:
    """Validate query limits, buffer bounds, and background-task intervals."""
    def int_check(value, key):
        if isinstance(value, bool): raise Exception(f"invalid {key}: expected integer")
        try: value = int(value)
        except Exception: raise Exception(f"invalid {key}: expected integer") from None
        if value < 1: raise Exception(f"invalid {key}: minimum 1")
        return value
    values = {key: int_check(getattr(app_state, key, None), key) for key in ("config_query_runner_read_limit", "config_export_limit", "config_sql_read_limit_default", "config_sql_read_limit_max", "config_sql_read_relation_fetch_limit_max", "config_postgres_buffer_flush_auto_sec", "config_uvicorn_workers", "config_request_body_max_kb", "config_request_form_max_kb", "config_api_cache_inmemory_max_kb")}
    if values["config_sql_read_limit_default"] > values["config_sql_read_limit_max"]: raise Exception("config_sql_read_limit_default must not exceed config_sql_read_limit_max")
    values = getattr(app_state, "_state", None) or vars(app_state)
    if "config_table" in values: raise ValueError("config_table was removed in Atom 9.0.0: set a table's buffer size in control.buffer_limit of config_postgres_schema_<name> ({table: rows})")
    moved = {"config_table_public_create_allowed": "control.public_create", "config_table_public_read_allowed": "control.public_read", "config_table_private_read_allowed": "control.private_read", "config_table_my_create_blocked": "control.my_create", "config_table_my_read_blocked": "control.my_read", "config_table_my_delete_all_allowed": "control.my_delete_all", "config_table_write_blocked": "nothing (the /admin routes reach every table; control.my_* opens tables to users)", "config_table_exclude_from_users_delete": "nothing (the users-delete worker skips users and log_users_delete)", "config_column_private_read_blocked": "read_blocked: [\"private\"] on the column", "config_column_int_mapping": "int_mapping on the column (users role: config_users_role_label; permissions: from config_api)", "config_postgres_db_log_api": "none (the database whose schema has log_api gets the API logs)"}
    moved.update({key: "control.buffer_limit" for key in values if key.startswith("config_buffer_limit_")})
    if "config_column_regex" in values: raise ValueError("config_column_regex removed in Atom 24.0.0: set regex and regex_message on each column in config_postgres_schema_<name> (users.password included: checked before it is hashed); delete it from config_extend.py and .env")
    moved.update({key: "control.retention_day" for key in values if key.startswith("config_retention_day_table_")})
    if found := [key for key in moved if key in values]: raise ValueError(f"{found[0]} removed: use {moved[found[0]]} in config_postgres_schema_<name>" + (f" (and {len(found) - 1} more: {', '.join(found[1:4])}{', ...' if len(found) > 4 else ''})" if len(found) > 1 else "") + "; delete it from config_extend.py and .env")
    login_roles = values.get("config_login_allowed_roles")
    if "config_login_allowed_roles" in values and not (isinstance(login_roles, (list, tuple)) and (list(login_roles) == ["*"] or login_roles and all(isinstance(role, int) and not isinstance(role, bool) for role in login_roles))): raise ValueError('config_login_allowed_roles must be ["*"] (every role) or a list of roles, e.g. [1, 2]')
    role_label = values.get("config_users_role_label")
    if "config_users_role_label" in values and (not isinstance(role_label, dict) or not all(isinstance(code, int) and not isinstance(code, bool) and isinstance(label, str) for code, label in role_label.items())): raise ValueError("config_users_role_label must be {role: \"label\"}, e.g. {1: \"Admin\", 2: \"User\"}")
    if "config_sql" in values: raise ValueError("config_sql was removed in Atom 9.0.0: its queries are Atom's own; set config_cache_row_limit_config, config_cache_row_limit_users_role, config_cache_row_limit_users_deactivated, config_cache_row_limit_users_deleted and config_profile_metadata_sql instead")
    if removed := [key for key in ("config_column_token_encode", "config_column_users_private_read", "config_column_single_update", "config_column_users_my_blocked", "config_column_users_blocked") if key in values]: raise ValueError(f"{', '.join(removed)} removed in Atom 24.0.0: list the users columns in config_users_token_column, config_users_private_read_column, config_users_update_alone_column; a column only an admin may change gets \"write_blocked\": [\"my\"], one no request may change \"write_blocked\": [\"my\", \"public\", \"private\", \"admin\"]; delete it from config_extend.py and .env")
    column_moved = {"config_column_read_blocked": "\"read_blocked\": [\"my\", \"public\", \"private\", \"admin\"] on each column to hide", "config_column_audit_blocked": "nothing: the audit columns (created_at, created_by_id, updated_at, updated_by_id, deleted_at, deleted_by_id) are always set by Atom", "config_column_admin": "\"write_blocked\": [\"my\", \"public\"] on each column only an admin may set", "config_column_ownership_read": "\"ownership\": [\"read\", ...] on each owner column (created_by_id is always the owner)", "config_column_ownership_update": "\"ownership\": [\"update\", ...] on each owner column", "config_column_ownership_delete": "\"ownership\": [\"delete\", ...] on each owner column"}
    if removed := [key for key in column_moved if key in values]: raise ValueError(f"{removed[0]} removed in Atom 24.0.0: use {column_moved[removed[0]]} in config_postgres_schema_<name>; delete it from config_extend.py and .env")
    for key in ("config_is_root_user", "config_is_users_password_log", "config_is_users_delete_log", "config_is_totp_clear"):
        if key in values and not isinstance(values[key], bool): raise ValueError(f"{key} must be True or False")
    users_columns = {col.get("name"): col for col in ((((values.get("config_postgres_schema_master") or {}).get("table") or {}).get("users") or {}).get("column") or []) if isinstance(col, dict)}
    for key in ("config_users_token_column", "config_users_private_read_column", "config_users_update_alone_column"):
        listed = values.get(key)
        if key in values and (not isinstance(listed, list) or not all(isinstance(column, str) for column in listed) or len(set(listed)) != len(listed)): raise ValueError(f"{key} must be a list of users column names, each once")
        if users_columns and (wrong := [column for column in listed or [] if column not in users_columns]): raise ValueError(f"{key}: {', '.join(wrong)} is not a column of users in config_postgres_schema_master")
    for column in values.get("config_users_private_read_column") or []:
        if column == "password" or "private" in ((users_columns.get(column) or {}).get("read_blocked") or []): raise ValueError(f"config_users_private_read_column: users.{column} is read_blocked for private, so /private/user-read can never show it")
    if removed := [key for key in ("config_inmemory_cache_cleanup_auto_sec", "config_schedule_check_sec") if key in values]: raise ValueError(f"{', '.join(removed)} removed in Atom 22.0.0: fixed in code (cache cleanup every 300 s, schedule check every 600 s); delete it from config_extend.py and .env")
    if removed := [key for key in ("config_webhook_timeout_sec", "config_webhook_retry_max", "config_webhook_retry_wait_sec", "config_webhook_poll_sec", "config_webhook_verify_tolerance_sec") if key in values]: raise ValueError(f"{', '.join(removed)} removed in Atom 22.0.0: webhook timing is fixed (10 s timeout, 8 retries from 60 s doubling, 5 s poll, 300 s signature tolerance); delete it from config_extend.py and .env")
    if removed := [key for key in ("config_permission_table", "config_permission_user_roles", "config_permission_user_column_blocked", "config_permission_table_write_allowed", "config_permission_user_create_roles", "config_table_permission_write_allowed", "config_column_users_permission_blocked") if key in values]: raise ValueError(f"{', '.join(removed)} removed in Atom 22.0.0 with the /permission routes: grant a user the id of the /admin route instead (users.permissions holds route ids only)")
    for key in ("config_cache_row_limit_config", "config_cache_row_limit_users_role", "config_cache_row_limit_users_deactivated", "config_cache_row_limit_users_deleted"):
        limit = values.get(key)
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0): raise ValueError(f"{key} must be an integer, 0 or more")
    for old_key, new_key in (("config_otp_retention_day", "control.retention_day.otp"), ("config_log_api_retention_day", "control.retention_day.log_api"), ("config_users_delete_retention_day", "config_retention_day_user_soft_deleted"), ("config_retention_day_otp", "control.retention_day.otp"), ("config_retention_day_log_api", "control.retention_day.log_api"), ("config_retention_day_script_run", "control.retention_day.script_run"), ("config_retention_day_users_delete", "config_retention_day_user_soft_deleted")):
        if old_key in values: raise ValueError(f"{old_key} was renamed to {new_key}; rename it in config_extend.py or .env")
    retention = getattr(app_state, "config_retention_day_user_soft_deleted", None)
    if retention is not None and (isinstance(retention, bool) or not isinstance(retention, int) or not 1 <= retention <= 36500): raise ValueError("config_retention_day_user_soft_deleted must be an integer from 1 to 36500, or None")
    otp_retention = ((((values.get("config_postgres_schema_master") or {}).get("control") or {}).get("retention_day")) or {}).get("otp")
    if otp_retention and otp_retention * 86400 <= getattr(app_state, "config_otp_expiry_sec", 0): raise ValueError("control.retention_day.otp must exceed the OTP expiry window (config_otp_expiry_sec)")
    keep_alive = getattr(app_state, "config_uvicorn_timeout_keep_alive_sec", 250)
    if isinstance(keep_alive, bool) or not isinstance(keep_alive, int) or keep_alive < 1: raise Exception("config_uvicorn_timeout_keep_alive_sec must be an integer, 1 or more")
    query_timeout = getattr(app_state, "config_postgres_query_timeout_sec", 0)
    if isinstance(query_timeout, bool) or not isinstance(query_timeout, (int, float)) or query_timeout < 0: raise Exception("config_postgres_query_timeout_sec must be a number, 0 or more (0 means no limit)")
    token_cache_max = getattr(app_state, "config_token_cache_max", 0)
    if isinstance(token_cache_max, bool) or not isinstance(token_cache_max, int) or token_cache_max < 0: raise Exception("config_token_cache_max must be an integer, 0 or more (0 turns the token cache off)")
    buffer_rows_max = getattr(app_state, "config_buffer_rows_max", None)
    if buffer_rows_max is not None and (isinstance(buffer_rows_max, bool) or not isinstance(buffer_rows_max, int) or buffer_rows_max < 1000): raise Exception("config_buffer_rows_max must be an integer of at least 1000")
    secret = getattr(app_state, "config_token_secret_key", None)
    if getattr(app_state, "config_is_prod", True) is not False and secret not in (None, "") and len(str(secret).encode()) < 32:
        raise Exception("config_token_secret_key must be at least 32 bytes in production (a short key lets tokens be forged); generate one with: python3 -c \"import secrets; print(secrets.token_urlsafe(48))\"")
    return

def func_check_api_config(*, app: FastAPI) -> None:
    """Validate registered API middleware configuration and its Redis dependencies."""
    config_api = getattr(app.state, "config_api", {})
    schemes = getattr(app.state, "config_webhook_verify_scheme", None) or {}
    if not isinstance(schemes, dict): raise Exception("config_webhook_verify_scheme must be a dict of scheme name to scheme")
    for name, scheme in schemes.items(): func_webhook_verify_scheme_check(name=name, scheme=scheme)
    if not isinstance(config_api, dict): raise Exception("config_api must be dict")
    route_paths = {route.path for route in func_app_route_list(app=app) if hasattr(route, "path")}
    websocket_paths = {route.path for route in func_app_route_list(app=app) if isinstance(route, WebSocketRoute)}
    # ids under 200 belong to Atom, so a new Atom route never takes a project's id
    project_paths = {route.path for route in func_app_route_list(app=app) if hasattr(route, "path") and getattr(getattr(route, "endpoint", None), "__module__", "").startswith("router_extend")}
    api_ids = []
    token_columns = func_postgres_users_access(config_users_token_column=getattr(app.state, "config_users_token_column", None))["token"]
    user_mode_allowed = ("redis", "realtime", "inmemory", "token")
    for key in ("config_api_global_user_check_deleted", "config_api_global_user_check_deactivated"):
        value = getattr(app.state, key, None)
        if value is not None and value not in user_mode_allowed: raise Exception(f"invalid {key}: {value!r}, allowed: {', '.join(user_mode_allowed)} or None")
        column = key.removeprefix("config_api_global_user_check_") + "_at"
        if value == "token" and column not in token_columns: raise Exception(f"{key} is token: add \"{column}\" to config_users_token_column")
    api_mode_allowed = ("redis", "inmemory")
    api_keys_allowed = ("id", "is_active", "auth", "is_connection_param", "user_check_role", "user_check_permission", "user_check_deactivated", "user_check_deleted", "cache", "rate_limit", "is_log_api", "webhook_verify", "ip_allow", "token_verify")
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
        if "is_token" in cfg or "is_api_key" in cfg: raise Exception(f'{path}: is_token and is_api_key were replaced by auth in Atom 17 ("is_token": True -> "auth": ["jwt"], "is_token": False -> "auth": [], "is_api_key": True -> add "api_key" to auth)')
        for key in cfg.keys():
            if key not in api_keys_allowed: raise Exception(f"{path} invalid config key: {key}")
        if "id" not in cfg: raise Exception(f"{path} missing required key: id")
        api_id = int_check(cfg["id"], f"{path} id", 1)
        if api_id in api_ids: raise Exception(f"duplicate api id: {api_id}")
        if path in project_paths and api_id < 200: raise Exception(f"{path} id {api_id}: project routes use ids from 200 (below 200 is Atom's)")
        api_ids.append(api_id)
        if "is_active" in cfg: flag_check(cfg["is_active"], f"{path} is_active")
        if path in websocket_paths:
            # the HTTP middleware never runs for websockets, so only id and is_active (checked inside the socket) mean anything
            for key in cfg:
                if key not in ("id", "is_active"): raise Exception(f"config_api {path}: websocket routes accept only id and is_active ({key} is HTTP-only; check it inside the socket)")
            continue
        if "is_connection_param" in cfg: flag_check(cfg["is_connection_param"], f"{path} is_connection_param")
        if "is_log_api" in cfg: flag_check(cfg["is_log_api"], f"{path} is_log_api")
        if "auth" not in cfg: raise Exception(f'{path} missing required key: auth ([] public, ["jwt"], ["api_key"] or ["jwt", "api_key"])')
        auth = cfg["auth"]
        if not isinstance(auth, (list, tuple)) or len(set(auth)) != len(auth) or any(a not in ("jwt", "api_key") for a in auth): raise Exception(f'{path} invalid auth: {auth!r}, expected a list of "jwt" and/or "api_key" ([] for public)')
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
        if path.startswith("/admin/") and not (cfg.get("user_check_permission") or cfg.get("user_check_role")): raise Exception(f"{path}: admin routes need user_check_permission or user_check_role (Atom's use the permission; an admin route never opens to every logged-in user)")
        if "webhook_verify" in cfg:
            verify = cfg["webhook_verify"]
            if not isinstance(verify, dict) or set(verify) != {"scheme", "secret"}: raise Exception(f'{path} invalid webhook_verify: expected {{"scheme": <name in config_webhook_verify_scheme>, "secret": <config_ setting holding the secret>}}')
            if verify["scheme"] not in (getattr(app.state, "config_webhook_verify_scheme", None) or {}): raise Exception(f"{path} webhook_verify: unknown scheme {verify['scheme']!r}; add it to config_webhook_verify_scheme")
            if not isinstance(verify["secret"], str) or not verify["secret"].startswith("config_"): raise Exception(f"{path} webhook_verify: secret must name a config_ setting (the secret itself goes in .env), such as config_webhook_secret_stripe")
            if auth: raise Exception(f"{path} webhook_verify: auth must be [] (the signature is the credential)")
        if "ip_allow" in cfg:
            ip_allow = cfg["ip_allow"]
            if not isinstance(ip_allow, list) or not ip_allow or not all(isinstance(item, str) for item in ip_allow): raise Exception(f'{path} invalid ip_allow: expected a non-empty list of IP addresses or CIDR ranges, such as ["203.0.113.0/24"]')
            for item in ip_allow:
                try: ipaddress.ip_network(item, strict=False)
                except ValueError: raise Exception(f"{path} invalid ip_allow entry: {item!r}") from None
        if "token_verify" in cfg:
            token_verify = cfg["token_verify"]
            if not isinstance(token_verify, dict) or "secret" not in token_verify or set(token_verify) - {"secret", "in", "name"}: raise Exception(f'{path} invalid token_verify: expected {{"secret": <config_ setting holding the token>, "in": "header" or "query", "name": <header or query name>}}')
            if not isinstance(token_verify["secret"], str) or not token_verify["secret"].startswith("config_"): raise Exception(f"{path} token_verify: secret must name a config_ setting (the token itself goes in .env), such as config_webhook_token_devices")
            if token_verify.get("in", "header") not in ("header", "query"): raise Exception(f"{path} token_verify: in must be header or query")
            if "name" in token_verify and not (isinstance(token_verify["name"], str) and re.fullmatch(r"[A-Za-z0-9_-]+", token_verify["name"])): raise Exception(f"{path} token_verify: invalid name {token_verify['name']!r}")
            if token_verify.get("in") == "query" and "token" not in str(token_verify.get("name") or "token").lower(): raise Exception(f"{path} token_verify: a query name must contain 'token', so request logs hide its value")
        if not auth and any(cfg.get(key) for key in ("user_check_role", "user_check_permission", "user_check_deactivated", "user_check_deleted")): raise Exception(f"{path}: a role, permission, deactivated or deleted check needs a credential (a non-empty auth)")
        if "user_check_permission" in cfg:
            permission_val = cfg["user_check_permission"]
            if not isinstance(permission_val, dict) or set(permission_val) != {"mode"}: raise Exception(f"{path} invalid user_check_permission: expected {{\"mode\": \"token\"}} or {{\"mode\": \"realtime\"}}")
            if permission_val["mode"] not in ("token", "realtime"): raise Exception(f"{path} invalid user_check_permission mode: {permission_val['mode']}, allowed: token, realtime")
            if permission_val["mode"] == "token" and "permissions" not in token_columns: raise Exception(f"{path} user_check_permission: add \"permissions\" to config_users_token_column")
        for key in ("user_check_deactivated", "user_check_deleted"):
            u_val = cfg.get(key)
            if u_val:
                mode = u_val.get("mode") if isinstance(u_val, dict) else (u_val[0] if isinstance(u_val, (list, tuple)) else None)
                if mode not in user_mode_allowed: raise Exception(f"{path} invalid {key} mode: {mode}")
                if mode == "redis": requires_redis_user_state = True
                if mode == "inmemory": inmemory_list.append(f"{path} {key}")
        c_val = cfg.get("cache")
        if c_val:
            if not isinstance(c_val, dict): raise Exception(f"{path} invalid cache format: {{\"mode\": \"inmemory\" or \"redis\", \"ttl_sec\": n, \"is_per_user\": bool}}")
            if unknown := sorted(set(c_val) - {"mode", "ttl_sec", "is_per_user"}): raise Exception(f"{path} cache: unknown key {', '.join(unknown)} (mode, ttl_sec, is_per_user)")
            mode, ttl, is_per_user = c_val.get("mode"), c_val.get("ttl_sec", 0), c_val.get("is_per_user", False)
            if mode not in api_mode_allowed: raise Exception(f"{path} invalid cache mode: {mode}")
            ttl = int_check(ttl, f"{path} cache ttl", 1)
            if ttl > 315360000: raise Exception(f"{path} cache ttl exceeds 10 years")
            flag_check(is_per_user, f"{path} cache is_per_user flag")
            if mode == "redis": requires_redis = True
            if mode == "inmemory": inmemory_list.append(f"{path} cache")
        r_val = cfg.get("rate_limit")
        if r_val:
            if not isinstance(r_val, dict): raise Exception(f"{path} invalid rate_limit format: {{\"mode\": \"inmemory\" or \"redis\", \"limit\": n, \"window_sec\": n}}")
            if unknown := sorted(set(r_val) - {"mode", "limit", "window_sec"}): raise Exception(f"{path} rate_limit: unknown key {', '.join(unknown)} (mode, limit, window_sec)")
            mode, limit, window = r_val.get("mode"), r_val.get("limit", 0), r_val.get("window_sec", 0)
            if mode not in api_mode_allowed: raise Exception(f"{path} invalid rate_limit mode: {mode}")
            int_check(limit, f"{path} rate_limit limit", 1)
            window = int_check(window, f"{path} rate_limit window", 1)
            if window > 31536000: raise Exception(f"{path} rate_limit window exceeds 1 year")
            if mode == "redis": requires_redis_ratelimiter = True
            if mode == "inmemory": inmemory_list.append(f"{path} rate_limit")
    for path in route_paths:
        if path not in config_api:
            raise Exception(f"CRITICAL: Route '{path}' is missing from config_api. All routes must be explicitly configured.")
    redis_url_dict = getattr(app.state, "config_redis_url_dict", None) or {}
    if requires_redis and not redis_url_dict.get("api_response"):
        raise Exception("config_api uses redis cache mode but config_redis_url_api_response is missing")
    if requires_redis_user_state and not redis_url_dict.get("user_state"):
        raise Exception("config_api uses redis user state check but config_redis_url_user_state is missing")
    if requires_redis_ratelimiter and not redis_url_dict.get("ratelimiter"):
        raise Exception("config_api uses redis rate limiting but config_redis_url_ratelimiter is missing")
    redis_urls_required = []
    if requires_redis: redis_urls_required.append("config_redis_url_api_response")
    if requires_redis_user_state: redis_urls_required.append("config_redis_url_user_state")
    if requires_redis_ratelimiter: redis_urls_required.append("config_redis_url_ratelimiter")
    for key in redis_urls_required:
        url = redis_url_dict.get(key.removeprefix("config_redis_url_"))
        if not isinstance(url, str) or not url.strip().lower().startswith(("redis://", "rediss://", "unix://")):
            raise Exception(f"{key} must be a valid Redis URL")
    workers = int(getattr(app.state, "config_uvicorn_workers", 1) or 1)
    if workers > 1 and "/my/message-socket" in config_api and config_api["/my/message-socket"].get("is_active", True):
        raise Exception(f"config_uvicorn_workers={workers}: /my/message-socket delivers only to sockets in the same worker; keep it inactive or run 1 worker")
    if workers > 1 and inmemory_list:
        raise Exception(f"config_uvicorn_workers={workers} needs state shared across workers; inmemory is per worker. Switch these to redis (user checks may also use realtime or token): {', '.join(inmemory_list)}")
    return

async def func_check_postgres_connections(*, app_state: State, client_postgres_dict: dict) -> None:
    """Warn when every worker's pools together could exceed a Postgres server's max_connections."""
    workers = int(getattr(app_state, "config_uvicorn_workers", 1) or 1)
    pools_max = sum(pool.get_max_size() for pool in client_postgres_dict.values() if pool)    # each pool's own size (config_postgres_pool_max_size_<name> or the shared one)
    for name, pool in client_postgres_dict.items():
        if pool is None: continue
        try:
            async with pool.acquire(timeout=5) as conn:
                max_connections = int(await conn.fetchval("SHOW max_connections", timeout=5))
                reserved = int(await conn.fetchval("SHOW superuser_reserved_connections", timeout=5))
        except Exception as e:
            print(f"⚠️ postgres {name}: connection limit check skipped: {e}")
            continue
        needed = workers * pools_max
        if needed > max_connections - reserved:
            print(f"⚠️ postgres {name}: {workers} workers x {pools_max} connections across {len(client_postgres_dict)} pools = up to {needed}, above max_connections {max_connections} minus {reserved} reserved; lower config_postgres_pool_max_size (or config_postgres_pool_max_size_<name>) or config_uvicorn_workers")
    return

def func_check_config_extend_alias(*, config_module, config_extend_module) -> None:
    """Stop startup when config_extend.py names an imported base value config_*: every config_* name is read as a setting, so aliases must not start with config_."""
    if config_module is None or config_extend_module is None: return
    base = {id(value): key for key, value in vars(config_module).items() if key.startswith("config_") and isinstance(value, (dict, list, set, tuple))}
    for key, value in vars(config_extend_module).items():
        if key.startswith("config_") and key not in vars(config_module) and id(value) in base:
            raise Exception(f"config_extend.py: {key} is an alias of {base[id(value)]}; name it base_{base[id(value)]} (names starting with config_ are read as settings)")
    return

def func_check_config_extend_keeps_atom(*, config_module, config_extend_module) -> None:
    """Stop startup when config_extend.py defines config_api, config_postgres_schema_master or config_users_role_label without Atom's entries.

    config_api: Atom's routes. config_postgres_schema_master: Atom's parts (table, sql, control) and, inside each, Atom's
    tables, SQL entries, switches and control.extension names; one of Atom's tables may live in another database's config_postgres_schema_<name> instead (log_api in the database for logs). config_users_role_label: Atom's role codes. Values and labels may change and anything may be added.
    What counts as Atom's is read from config.py on every start, so new entries there are covered without changing this check.
    """
    if config_module is None or config_extend_module is None: return
    def missing(atom, extended, path):    # Atom's entries absent from extended: dict keys, or list items
        if isinstance(atom, dict): return [f"{path}{key}" for key in atom if not isinstance(extended, dict) or key not in extended]
        if isinstance(atom, list): return [f"{path}{item}" for item in atom if not isinstance(extended, (list, tuple)) or item not in extended]
        return []
    fixes = {"config_api": "{**base_config_api, ...}", "config_postgres_schema_master": "{**base_config_postgres_schema_master, \"table\": {**base_config_postgres_schema_master[\"table\"], ...}}", "config_users_role_label": "{**base_config_users_role_label, 2: \"User\"}"}
    for name, fix in fixes.items():
        if name not in vars(config_extend_module): continue
        atom, extended = getattr(config_module, name), getattr(config_extend_module, name)
        if name == "config_postgres_schema_master":    # two levels: each part, then each entry inside it; a table may be in another database's schema
            elsewhere = {table for key, schema in vars(config_extend_module).items() if key.startswith("config_postgres_schema_") and key != name and isinstance(schema, dict) for table in schema.get("table") or {}}
            dropped = missing(atom, extended, "")
            dropped += [item for part, value in atom.items() if isinstance(extended, dict) and part in extended for item in missing(value, extended[part], f"{part}.") if not (part == "table" and item.removeprefix("table.") in elsewhere)]
            if isinstance(extended, dict) and isinstance(extended.get("control"), dict) and "extension" in extended["control"]: dropped += missing((atom.get("control") or {}).get("extension"), extended["control"]["extension"], "control.extension.")
            if isinstance(extended, dict) and isinstance(extended.get("control"), dict):    # access lists keep Atom's tables (a project adds its own with [*base_config_postgres_schema_master["control"]["my_read"], ...]), except a table moved to another database
                for key in sorted(CONTROL_ACCESS):
                    if key in extended["control"]: dropped += [item for item in missing((atom.get("control") or {}).get(key), extended["control"][key], f"control.{key}.") if item.removeprefix(f"control.{key}.") not in elsewhere]
            label = "entries"
        elif name == "config_users_role_label":
            dropped, label = missing(atom, extended, ""), "codes"
        else:
            dropped, label = missing(atom, extended, ""), "routes"
        if dropped: raise Exception(f"config_extend.py: {name} drops {len(dropped)} of Atom's {label} ({', '.join(str(item) for item in dropped[:5])}{', ...' if len(dropped) > 5 else ''}); fix: {fix}")
    return

def func_check(*, app: FastAPI) -> None:
    """Validate database, runtime, and API configuration before client initialization."""
    func_check_postgres_schema(app_state=app.state)    # every database's schema: caught here, in script.check and CI, before any database
    func_check_config_extend_alias(config_module=sys.modules.get("config"), config_extend_module=sys.modules.get("config_extend"))
    func_check_config_extend_keeps_atom(config_module=sys.modules.get("config"), config_extend_module=sys.modules.get("config_extend"))
    func_check_database_config(app_state=app.state)
    func_check_runtime_config(app_state=app.state)
    func_schedule_read(values=getattr(app.state, "_state", None) or vars(app.state))    # a bad config_schedule_* value or a missing script stops startup
    func_check_api_config(app=app)
    return
