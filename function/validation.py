"""Atom validation functions."""

async def func_regex_check(*, config_column_regex: dict, obj_list: list) -> None:
    """Validate fields in a list of objects against regex patterns defined in config."""
    import re
    if not config_column_regex: return None
    for obj in obj_list:
        for key, regex_info in config_column_regex.items():
            val = obj.get(key)
            if val is not None:
                pattern = regex_info[0]
                error_msg = regex_info[1]
                if not re.match(pattern, str(val)):
                    raise Exception(error_msg)
    return None

def func_validate_restricted_columns(*, app_state: any, obj_list: list) -> None:
    """Validate that object list does not contain restricted columns configured in config_column_admin."""
    config_column_admin = getattr(app_state, "config_column_admin", set()) or set()
    if restricted_key := next((key for item in obj_list for key in item if key in config_column_admin), None):
        raise Exception(f"unauthorized update to restricted field: {restricted_key}")

def func_check_table_permission(*, app_state: any, table: str, relation: list = None, scope: str = "public", action: str = "read") -> None:
    """Validate if table and relation access is allowed for given scope ('public', 'private', 'my') and action ('read', 'create', 'delete_all')."""
    verb_map = {"create": "creation", "read": "read", "delete_all": "delete all"}
    verb = verb_map.get(action, action.replace("_", " "))
    blocked_attr = f"config_table_{scope}_{action}_blocked"
    blocked_tables = getattr(app_state, blocked_attr, None)
    if blocked_tables is not None:
        if "*" in blocked_tables or table in blocked_tables:
            raise Exception(f"{verb} disabled for table: {table}")
        if relation:
            for rel in relation:
                parts = [p.strip() for p in rel.split(",", 4)]
                if len(parts) >= 2 and ("*" in blocked_tables or parts[1] in blocked_tables):
                    raise Exception(f"relation read disabled for table: {parts[1]}")
        return
    config_attr = f"config_table_{scope}_{action}_allowed"
    enabled_tables = getattr(app_state, config_attr, []) or []
    if "*" not in enabled_tables and table not in enabled_tables:
        raise Exception(f"{verb} disabled for table: {table}")
    if relation:
        for rel in relation:
            parts = [p.strip() for p in rel.split(",", 4)]
            if len(parts) >= 2 and "*" not in enabled_tables and parts[1] not in enabled_tables:
                raise Exception(f"relation read disabled for table: {parts[1]}")

def func_check_table_column_exists(*, app_state: any = None, cache_postgres_schema: dict = None, table: str, column: str, purpose: str = None) -> None:
    """Validate that table schema contains specified column."""
    cache = cache_postgres_schema if cache_postgres_schema is not None else (getattr(app_state, "cache_postgres_schema", {}) or {})
    if table not in cache:
        raise Exception(f"table '{table}' not found")
    if column not in cache[table]:
        msg = f"table '{table}' lacks required '{column}' column"
        if purpose: msg += f" for {purpose}"
        raise Exception(msg)

async def func_check_user_update_permission(*, app_state: any, table: str, obj_list: list, scope: str = "admin", otp: int = None, user_id: int = None) -> None:
    """Validate permissions, sensitive fields, and OTP requirements for user and object updates."""
    if any("password" in item for item in obj_list) and any(len(item) != 2 or "id" not in item or "password" not in item for item in obj_list):
        raise Exception("password update requires exactly two fields (id, password)")
    if table == "users":
        if scope == "my":
            if len(obj_list) > 1:
                raise Exception("multi-object user update restricted")
            if user_id is not None and str(obj_list[0].get("id")) != str(user_id):
                raise Exception("ownership issue: cannot update other users")
            if any(key in getattr(app_state, 'config_column_single_update', []) for key in obj_list[0]) and len(obj_list[0]) != 2:
                raise Exception("sensitive fields must be updated individually (item length 2 required)")
        is_otp_required = getattr(app_state, "config_is_otp_require_users_update", False) if scope == "admin" else True
        if is_otp_required and any(key in obj_list[0] for key in ("email", "mobile")):
            if len(obj_list) > 1:
                raise Exception("multi-object user update restricted")
            if len(obj_list[0]) != 2:
                raise Exception("sensitive fields must be updated individually (item length 2 required)")
            await app_state.func_otp_verify(
                client_postgres=app_state.client_postgres,
                otp=otp,
                email=obj_list[0].get("email"),
                mobile=obj_list[0].get("mobile"),
                config_otp_expiry_sec=app_state.config_otp_expiry_sec,
                config_otp_static=app_state.config_otp_static
            )

def func_check_user_delete_permission(*, app_state: any, table: str, scope: str = "admin", ids: list = None, user_id: int = None) -> None:
    """Validate single-account deletion through my and admin object-delete."""
    if table == "users":
        if scope not in ("my", "admin"): raise Exception("users table delete restricted; use /my/object-delete or /admin/object-delete")
        if not app_state.config_is_user_delete: raise Exception("users hard delete disabled")
        if not ids or len(ids) != 1: raise Exception("users table delete requires exactly one id")
        if scope == "my" and (user_id is None or int(ids[0]) != int(user_id)): raise Exception("users table delete allowed only for own account")

def func_check_batch_limit(*, app_state: any, items: list) -> None:
    """Ensure batch item list length does not exceed config_batch_item_limit."""
    limit = getattr(app_state, "config_batch_item_limit", None)
    if limit and len(items) > limit:
        raise Exception(f"maximum {limit} objects allowed")
