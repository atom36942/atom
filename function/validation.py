# import
import re
from starlette.datastructures import State
from .middleware import func_api_error

# function
async def func_regex_check(*, column_regex: dict, obj_list: list) -> None:
    """Validate fields in a list of objects against regex patterns defined in config."""
    if not column_regex: return
    for obj in obj_list:
        for key, regex_info in column_regex.items():
            val = obj.get(key)
            if val is not None:
                pattern = regex_info[0]
                error_msg = regex_info[1]
                if not re.match(pattern, str(val)):
                    raise Exception(error_msg)
    return

def func_column_regex(*, app_state: State, table: str, connection: str = None) -> dict:
    """The format rules of one table's columns, {column: [pattern, message]}: each column's regex and regex_message in config_postgres_schema_<connection> (users.password included, checked before it is hashed)."""
    return ((getattr(app_state, "cache_column_regex", None) or {}).get(connection or "master") or {}).get(table) or {}

def func_role_allowed_values(*, roles: list) -> list | None:
    """The allowed values of a role parameter: None (any role) when roles is ["*"], else the list itself."""
    return None if "*" in (roles or []) else roles

def func_check_table_access(*, app_state: State, connection: str = None, table: str, group: str, action: str, relation: list = None) -> None:
    """Refuse a table (and every table a read joins through relation) not listed in control.<group>_<action> (public_create, private_read, my_update, admin_read, ...) of config_postgres_schema_<connection>: a table is closed unless listed, for every group, admin included (["*"] in admin_read: every table of that database). A database without a schema is closed to every table route (403)."""
    database = connection or "master"
    rules = (getattr(app_state, "cache_postgres_table_rule", None) or {}).get(database)
    tables = [(table, action)] + [(parts[1], "read") for rel in relation or [] if len(parts := [p.strip() for p in rel.split(",", 4)]) >= 2]
    for name, needed in tables:
        if rules is None: raise func_api_error(message=f"{group} {needed} not allowed for table: {name} (database {database} has no config_postgres_schema_{database}: add one whose control lists the tables to open)", status_code=403)
        if needed in ((rules.get(name) or {}).get(group) or []) or needed in ((rules.get("*") or {}).get(group) or []): continue
        raise func_api_error(message=f"{group} {needed} not allowed for table: {name} (add \"{name}\" to control.{group}_{needed} in config_postgres_schema_{database})", status_code=403)

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
