# import
import re
from starlette.datastructures import State
from .middleware import func_api_error

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

def func_check_table_access(*, app_state: State, connection: str = None, table: str, group: str, action: str, relation: list = None) -> None:
    """Refuse a table (and every table a read joins through relation) whose schema does not list action under group (public, private, my, admin) in config_postgres_schema_<connection>: a table is closed unless listed. 403."""
    database = connection or "master"
    rules = (getattr(app_state, "cache_postgres_table_rule", None) or {}).get(database) or {}
    tables = [(table, action)] + [(parts[1], "read") for rel in relation or [] if len(parts := [p.strip() for p in rel.split(",", 4)]) >= 2]
    for name, needed in tables:
        if needed not in ((rules.get(name) or {}).get(group) or []): raise func_api_error(message=f"{group} {needed} not allowed for table: {name} (add \"{needed}\" to \"{group}\" of {name} in config_postgres_schema_{database})", status_code=403)

def func_check_table_column_exists(*, app_state: State = None, cache_postgres_schema: dict = None, table: str, column: str, purpose: str = None) -> None:
    """Validate that table schema contains specified column."""
    cache = cache_postgres_schema if cache_postgres_schema is not None else (app_state.cache_postgres_schema_dict.get("master", {}) or {})
    if table not in cache:
        raise Exception(f"table '{table}' not found")
    if column not in cache[table]:
        msg = f"table '{table}' lacks required '{column}' column"
        if purpose: msg += f" for {purpose}"
        raise Exception(msg)

def func_buffer_limit(*, app_state: State, table: str, connection: str = None) -> int:
    """Rows a table's create buffer holds before it is written: the table's buffer_limit in config_postgres_schema_<connection>, else 100."""
    rule = ((getattr(app_state, "cache_postgres_table_rule", None) or {}).get(connection or "master") or {}).get(table) or {}
    return rule.get("buffer_limit") or 100

def func_check_audit_columns(*, app_state: State, obj_list: list) -> None:
    """Refuse a column of config_column_audit_blocked (who and when a row was created, updated or deleted) in any request row, admin's included: Atom sets them, so they can't be forged: 400."""
    blocked = set(getattr(app_state, "config_column_audit_blocked", None) or [])
    if columns := sorted({c for obj in obj_list if isinstance(obj, dict) for c in obj if c in blocked}): raise func_api_error(message=f"{', '.join(columns)} is set by Atom, not by a request", status_code=400)

def func_check_table_not_users(*, table: str) -> None:
    """Refuse the users table in a generic object API: users rows are written only through their own APIs (/my/user-*, /admin/user-*)."""
    if table == "users": raise Exception("write disabled for table: users")

def func_check_honeypot(*, app_state: State, obj_list: list) -> list:
    """Refuse public rows whose hidden honeypot field (config_public_create_honeypot) was filled, as only bots fill it; drop the field from the rest."""
    key = getattr(app_state, "config_public_create_honeypot", None)
    if not key:
        return obj_list
    if any(str(item.get(key) or "").strip() for item in obj_list):
        raise Exception("refused")
    return [{column: value for column, value in item.items() if column != key} for item in obj_list]

def func_check_batch_limit(*, app_state: State, items: list) -> None:
    """Ensure batch item list length does not exceed config_batch_item_limit."""
    limit = getattr(app_state, "config_batch_item_limit", None)
    if limit and len(items) > limit:
        raise Exception(f"maximum {limit} objects allowed")
