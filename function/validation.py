# import
import re
from starlette.datastructures import State

# function
async def func_regex_check(*, config_column_regex: dict, obj_list: list) -> None:
    """Validate fields in a list of objects against regex patterns defined in config."""
    if not config_column_regex: return
    for obj in obj_list:
        for key, regex_info in config_column_regex.items():
            val = obj.get(key)
            if val is not None:
                pattern = regex_info[0]
                error_msg = regex_info[1]
                if not re.match(pattern, str(val)):
                    raise Exception(error_msg)
    return

def func_validate_restricted_columns(*, app_state: State, obj_list: list) -> None:
    """Validate that object list does not contain restricted columns configured in config_column_admin."""
    config_column_admin = getattr(app_state, "config_column_admin", set()) or set()
    if restricted_key := next((key for item in obj_list for key in item if key in config_column_admin), None):
        raise Exception(f"unauthorized update to restricted field: {restricted_key}")

def func_check_table_permission(*, app_state: State, table: str, relation: list = None, scope: str = "public", action: str = "read") -> None:
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

def func_check_table_column_exists(*, app_state: State = None, cache_postgres_schema: dict = None, table: str, column: str, purpose: str = None) -> None:
    """Validate that table schema contains specified column."""
    cache = cache_postgres_schema if cache_postgres_schema is not None else (app_state.cache_postgres_schema_dict.get("master", {}) or {})
    if table not in cache:
        raise Exception(f"table '{table}' not found")
    if column not in cache[table]:
        msg = f"table '{table}' lacks required '{column}' column"
        if purpose: msg += f" for {purpose}"
        raise Exception(msg)

def func_check_table_not_users(*, table: str, api: str) -> None:
    """Refuse the users table in a generic object API: users rows are written only through their own APIs (/my/user-*, /admin/user-*)."""
    if table == "users": raise Exception(f"users table: use {api}")

def func_check_batch_limit(*, app_state: State, items: list) -> None:
    """Ensure batch item list length does not exceed config_batch_item_limit."""
    limit = getattr(app_state, "config_batch_item_limit", None)
    if limit and len(items) > limit:
        raise Exception(f"maximum {limit} objects allowed")
