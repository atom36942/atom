# import
import contextlib
import hashlib
import re
from typing import Any
import asyncpg
from starlette.datastructures import State

# function
def func_postgres_schema_dict(*, values: dict) -> dict:
    """Every database's schema, {name: schema} from config_postgres_schema_<name>, master first: each is applied at startup to the database of config_postgres_url_<name>."""
    found = {key.removeprefix("config_postgres_schema_"): value for key, value in values.items() if key.startswith("config_postgres_schema_")}
    return dict(sorted(found.items(), key=lambda item: item[0] != "master"))

TABLE_ACCESS = {"public": ("create", "read"), "private": ("read",), "my": ("create", "read", "update", "delete", "delete_all"), "admin": ("create", "read", "update", "delete")}    # who calls (the route prefix) -> what they may do
CONTROL_ACCESS = {f"{group}_{action}": (group, action) for group, actions in TABLE_ACCESS.items() for action in actions}    # control key -> (group, action): public_create, ..., my_delete_all
CONTROL_SWITCHES = {"is_updated_at_set": True, "is_protected_delete_disabled": True, "is_truncate_disabled": True}    # control switch -> its default
CONTROL_ROW_LISTS = ("row_update_disabled", "row_delete_disabled")    # control keys that list tables of the schema's table part (database triggers: Atom manages those tables)
CONTROL_TABLE_LISTS = (*CONTROL_ACCESS, *CONTROL_ROW_LISTS)
CONTROL_WILDCARD = ("admin_create", "admin_read", "admin_update", "admin_delete")    # the only lists that may be ["*"] (every table of that database): admins already need the route's permission id; public, private and my name each table
CONTROL_TABLE_NUMBERS = {"row_delete_max": (1, None), "buffer_limit": (10, 5000), "retention_day": (1, 36500)}    # control keys {table: number} -> (lowest, highest)
CONTROL_KEYS = ("extension", *CONTROL_SWITCHES, *CONTROL_TABLE_LISTS, *CONTROL_TABLE_NUMBERS)
COLUMN_GROUPS = ("my", "public", "private", "admin")    # the route groups read_blocked / write_blocked may list
OWNERSHIP_ACTIONS = ("read", "update", "delete")    # the /my actions a column's ownership may list (created_by_id is always the owner)
COLUMN_KEYS = ("name", "datatype", "identity", "is_primary_key", "default", "generated", "old_name", "is_not_null", "unique", "index", "check", "allowed_values", "regex", "regex_message", "int_mapping", "read_blocked", "write_blocked", "ownership")
COLUMN_KEYS_REMOVED = {"is_primary": "is_primary_key", "is_mandatory": "is_not_null", "old": "old_name", "in": "allowed_values (a list)", "is_private_read_blocked": "read_blocked: [\"private\"]", "is_read_only": "write_blocked: [\"my\", \"public\", \"private\", \"admin\"]",
                       "users_access": "write_blocked: [\"my\"] for my_update_blocked; config_users_token_column, config_users_private_read_column, config_users_update_alone_column in config.py for token, private_read, update_alone"}
CONTROL_KEYS_REMOVED = {"is_truncate_table": "is_truncate_disabled (True = TRUNCATE blocked)", "is_root_user_create": "config_is_root_user in config.py", "is_root_user_delete_disabled": "config_is_root_user in config.py", "is_log_users_password": "config_is_users_password_log in config.py", "is_log_users_delete": "config_is_users_delete_log in config.py", "is_totp_clear": "config_is_totp_clear in config.py (# totp)"}
TABLE_KEYS_MOVED = {"public": "public_create / public_read", "private": "private_read", "my": "my_create, my_read, my_update, my_delete, my_delete_all", "row_lock": "row_update_disabled / row_delete_disabled", "row_delete_max": "row_delete_max: {table: number}", "buffer_limit": "buffer_limit: {table: number}", "retention_day": "retention_day: {table: days}"}
ATOM_UPDATED_TABLES = ("users", "otp", "script_run", "queue_job")    # Atom updates their rows itself, so row_update_disabled may not list them
TABLE_BUFFER_LIMIT = 100

def func_postgres_schema_columns(*, config_postgres_schema: dict) -> dict:
    """{table: its column list} of one schema (each table is {"column": [...]})."""
    return {name: spec.get("column") if isinstance(spec, dict) else spec for name, spec in ((config_postgres_schema or {}).get("table") or {}).items()}

def func_postgres_table_rule_dict(*, schemas: dict) -> dict:
    """{database: {table: rules}} from every config_postgres_schema_<name>, for Atom's table routes: public / private / my / admin (the actions its control access lists give the table),
    row_delete_max, buffer_limit, retention_day (its control numbers), row_update_disabled / row_delete_disabled (bool), and from its columns read_blocked and write_blocked ({group: [columns]}) and ownership ({action: [columns]}), is_managed (in the table part).
    A table only named in an access list (made outside Atom) has no column rules. ["*"] in an admin list is kept as the entry "*" ({"admin": [its actions]}). A database without a schema has no entry: every table route refuses it."""
    rules = {}
    for name, schema in schemas.items():
        control = (schema or {}).get("control") or {}
        managed = func_postgres_schema_columns(config_postgres_schema=schema)
        named = [table for key in CONTROL_ACCESS for table in control.get(key) or [] if table != "*"]
        rules.setdefault(name, {})    # every database with a schema has its own entry, even without tables yet
        for table in [*managed, *[t for t in dict.fromkeys(named) if t not in managed]]:
            columns = [col for col in managed.get(table) or [] if isinstance(col, dict)]
            rule = {group: [action for key, (g, action) in CONTROL_ACCESS.items() if g == group and table in (control.get(key) or [])] for group in TABLE_ACCESS}
            rule.update({key: (control.get(key) or {})[table] for key in CONTROL_TABLE_NUMBERS if table in (control.get(key) or {})})
            rule.update({key: table in (control.get(key) or []) for key in CONTROL_ROW_LISTS})
            for key in ("read_blocked", "write_blocked"): rule[key] = {group: [col["name"] for col in columns if group in (col.get(key) or [])] for group in COLUMN_GROUPS}
            has_owner = table not in managed or any(col.get("name") == "created_by_id" for col in columns)    # an outside table: created_by_id if it has one (the route checks the column)
            rule["ownership"] = {action: (["created_by_id"] if has_owner else []) + [col["name"] for col in columns if action in (col.get("ownership") or []) and col["name"] != "created_by_id"] for action in OWNERSHIP_ACTIONS}
            rule["is_managed"] = table in managed
            rules[name][table] = rule
        if wildcard := [CONTROL_ACCESS[key][1] for key in CONTROL_WILDCARD if "*" in (control.get(key) or [])]: rules[name]["*"] = {**{group: [] for group in TABLE_ACCESS}, "admin": wildcard, "read_blocked": {}, "write_blocked": {}, "ownership": {}, "is_managed": False}
    return rules

def func_postgres_control_table_check(*, schemas: dict, cache_postgres_schema_dict: dict) -> None:
    """Startup, once each database's tables are read: every table an access list names exists in that database (in the table part, or made outside Atom); a schema whose database has no config_postgres_url_<name> is skipped (startup refused it already)."""
    for name, schema in schemas.items():
        if name not in cache_postgres_schema_dict: continue
        existing = cache_postgres_schema_dict.get(name) or {}
        control = (schema or {}).get("control") or {}
        for key in CONTROL_ACCESS:
            if missing := [table for table in control.get(key) or [] if table != "*" and table not in existing]: raise Exception(f"config_postgres_schema_{name}: control.{key}: {', '.join(missing)} is not a table of database {name} (add it to the table part, or create it in that database)")
    return

def func_postgres_ownership_column_dict(*, rules: dict) -> dict:
    """{action: [columns]}: every column any table of any schema accepts as owner for a /my action (created_by_id first), for the ownership_column parameter's allowed values; each table's own list is checked per request."""
    found = {action: ["created_by_id"] for action in OWNERSHIP_ACTIONS}
    for tables in rules.values():
        for rule in tables.values():
            for action, columns in (rule.get("ownership") or {}).items():
                found[action] += [column for column in columns if column not in found[action]]
    return found

def func_postgres_log_database(*, schemas: dict) -> str | None:
    """The database whose schema has the log_api table (API logs go there), or None."""
    return next((name for name, schema in schemas.items() if "log_api" in ((schema or {}).get("table") or {})), None)

def func_postgres_int_mapping(*, schemas: dict, config_users_role_label: dict = None, config_api: dict = None) -> dict:
    """{database: {table: {column: {code: label}}}} for /info: each column's int_mapping, plus master users.role (config_users_role_label) and users.permissions (each config_api route with user_check_permission: its id -> its path)."""
    mapping = {}
    for name, schema in schemas.items():
        for table, columns in func_postgres_schema_columns(config_postgres_schema=schema).items():
            for col in columns or []:
                if isinstance(col.get("int_mapping"), dict): mapping.setdefault(name, {}).setdefault(table, {})[col["name"]] = col["int_mapping"]
    users = mapping.setdefault("master", {}).setdefault("users", {})
    if config_users_role_label: users["role"] = dict(config_users_role_label)
    users["permissions"] = {cfg["id"]: path for path, cfg in sorted((config_api or {}).items(), key=lambda item: item[1].get("id", 0) if isinstance(item[1], dict) else 0) if isinstance(cfg, dict) and cfg.get("user_check_permission") and isinstance(cfg.get("id"), int)}
    return mapping

def func_postgres_users_access(*, config_users_token_column: list = None, config_users_private_read_column: list = None, config_users_update_alone_column: list = None) -> dict:
    """{token, private_read, update_alone: [master.users columns]} from the flat settings config_users_token_column, config_users_private_read_column, config_users_update_alone_column; id is always first in token and private_read."""
    def listed(columns, with_id):
        names = [str(column) for column in columns or []]
        return (["id"] if with_id else []) + [column for column in dict.fromkeys(names) if not (with_id and column == "id")]
    return {"token": listed(config_users_token_column, True), "private_read": listed(config_users_private_read_column, True), "update_alone": listed(config_users_update_alone_column, False)}

def func_postgres_column_regex_dict(*, schemas: dict) -> dict:
    """{database: {table: {column: [pattern, message]}}}: each column's regex and regex_message (default "<column>: invalid format"), the format the API checks on create and update."""
    rules = {}
    for name, schema in schemas.items():
        for table, columns in func_postgres_schema_columns(config_postgres_schema=schema).items():
            for col in columns or []:
                if col.get("regex"): rules.setdefault(name, {}).setdefault(table, {})[col["name"]] = [col["regex"], col.get("regex_message") or f"{col['name']}: invalid format"]
    return rules

def func_postgres_schema_table_validate(*, table_name: str, spec: Any) -> None:
    """One table: {"column": [...]}, nothing else (who may use it and its row rules are lists in control)."""
    if not isinstance(spec, dict): raise Exception(f"{table_name} must be a dict with a column list: {{\"column\": [...]}} (Atom 23.0.0)")
    if moved := [key for key in ("admin", "users_delete_skip") if key in spec]: raise Exception(f"{table_name}.{moved[0]} removed in Atom 24.0.0: " + ("the /admin object routes reach every table of the schema (each route's permission id decides who); delete it" if moved[0] == "admin" else "the users-delete worker always skips users and log_users_delete; delete it"))
    if moved := [key for key in spec if key in TABLE_KEYS_MOVED]: raise Exception(f"{table_name}.{moved[0]} moved in Atom 24.0.0 to the schema's control: {TABLE_KEYS_MOVED[moved[0]]} (lists of tables); delete it from the table")
    if unknown := sorted(set(spec) - {"column"}): raise Exception(f"{table_name}: unknown key {', '.join(unknown)}; a table has only column")
    if not isinstance(spec.get("column"), list) or not spec["column"]: raise Exception(f"{table_name} needs a list of columns in column")
    return

def func_postgres_schema_control_validate(*, config_postgres_schema: dict) -> None:
    """The schema's control: extension (names), switches (bool), access and row lists (tables of this schema), numbers ({table: integer} in range), and the combinations that would break at runtime."""
    control = config_postgres_schema.get("control") or {}
    if not isinstance(control, dict): raise Exception("control must be a dict")
    if removed := [key for key in control if key in CONTROL_KEYS_REMOVED]: raise Exception(f"control.{removed[0]} removed in Atom 24.0.0: use {CONTROL_KEYS_REMOVED[removed[0]]}")
    if moved := [key for key in control if key.startswith(("table_row_", "table_delete_", "disable_table_", "is_enable_", "is_disable_"))]: raise Exception(f"control.{moved[0]} removed: use row_update_disabled / row_delete_disabled / row_delete_max or is_truncate_disabled")
    if unknown := sorted(set(control) - set(CONTROL_KEYS)): raise Exception(f"control: unknown key {', '.join(unknown)}; allowed: {', '.join(CONTROL_KEYS)}")
    if (extensions := control.get("extension")) is not None and (not isinstance(extensions, list) or not all(isinstance(name, str) and name for name in extensions)): raise Exception("control.extension must be a list of extension names")
    for key in CONTROL_SWITCHES:
        if key in control and not isinstance(control[key], bool): raise Exception(f"control.{key} must be True or False")
    tables = func_postgres_schema_columns(config_postgres_schema=config_postgres_schema)
    def unknown_tables(names): return [name for name in names if name not in tables]
    for key in CONTROL_TABLE_LISTS:
        if key not in control: continue
        value = control[key]
        if not isinstance(value, list) or not all(isinstance(name, str) and name for name in value) or len(set(value)) != len(value): raise Exception(f"control.{key} must be a list of table names, each once")
        if "*" in value and (key not in CONTROL_WILDCARD or value != ["*"]): raise Exception(f"control.{key}: \"*\" is allowed only as [\"*\"] in {', '.join(CONTROL_WILDCARD)} (name each table)")
        if wrong := [name for name in value if name != "*" and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)]: raise Exception(f"control.{key}: {wrong[0]!r} is not a table name")
        if key in CONTROL_ROW_LISTS and (wrong := unknown_tables(value)): raise Exception(f"control.{key}: {', '.join(wrong)} is not in this schema's table part (a database guard needs a table Atom manages)")
    for key, (low, high) in CONTROL_TABLE_NUMBERS.items():
        if key not in control: continue
        value = control[key]
        if not isinstance(value, dict): raise Exception(f"control.{key} must be {{table: number}}")
        if wrong := unknown_tables(value): raise Exception(f"control.{key}: {', '.join(wrong)} is not in this schema's table part (Atom manages only those)")
        for table, number in value.items():
            if isinstance(number, bool) or not isinstance(number, int) or number < low or (high and number > high): raise Exception(f"control.{key}.{table} must be an integer from {low}" + (f" to {high}" if high else " up"))
    if writes := [f"{key}" for key in CONTROL_ACCESS if CONTROL_ACCESS[key][1] != "read" and "users" in (control.get(key) or [])]: raise Exception(f"control.{writes[0]}: users not allowed; users rows are written only through /my/user-* and /admin/user-*")
    if wrong := [table for table in control.get("row_update_disabled") or [] if table in ATOM_UPDATED_TABLES]: raise Exception(f"control.row_update_disabled: {wrong[0]} not allowed; Atom updates its rows itself")
    for table in control.get("retention_day") or {}:
        if table == "users": raise Exception("control.retention_day: users not allowed; it would delete users by age")
        if table in (control.get("row_delete_disabled") or []): raise Exception(f"control.retention_day: {table} is in row_delete_disabled, so cleanup could never delete its rows")
        if table in (control.get("row_delete_max") or {}): raise Exception(f"control.retention_day: {table} is in row_delete_max; cleanup deletes in batches that would trip it")
        if "created_at" not in {col.get("name") for col in tables[table] or [] if isinstance(col, dict)}: raise Exception(f"control.retention_day: {table} needs a created_at column (rows older than the days are deleted)")
    return

def func_postgres_schema_config_validate(*, config_postgres_schema: dict) -> None:
    """Validate configured tables, columns, indexes, unique keys and control before database changes."""
    if not isinstance(config_postgres_schema, dict): raise Exception("schema missing: a dict with table, control and sql (each optional)")
    if "extension" in config_postgres_schema: raise Exception("extension moved in Atom 24.0.0: put the list in control: \"control\": {\"extension\": [...], ...}")
    if unknown := sorted(set(config_postgres_schema) - {"table", "control", "sql"}): raise Exception(f"schema: unknown part {', '.join(unknown)}; a schema has table, control and sql")
    if not isinstance(config_postgres_schema.get("table", {}), dict): raise Exception("table must be a dict {table: {\"column\": [...]}}")
    for table_name, spec in (config_postgres_schema.get("table") or {}).items(): func_postgres_schema_table_validate(table_name=table_name, spec=spec)
    func_postgres_schema_control_validate(config_postgres_schema=config_postgres_schema)
    tables = func_postgres_schema_columns(config_postgres_schema=config_postgres_schema)
    reserved = {"all", "analyze", "and", "any", "as", "asc", "asymmetric", "authorization", "binary", "both", "case", "cast", "check", "collate", "collation", "column", "concurrently", "constraint", "create", "cross", "current_catalog", "current_date", "current_role", "current_schema", "current_time", "current_timestamp", "current_user", "default", "deferrable", "desc", "distinct", "do", "else", "end", "except", "false", "fetch", "for", "foreign", "freeze", "from", "full", "grant", "group", "having", "ilike", "in", "initially", "inner", "intersect", "into", "is", "isnull", "join", "lateral", "leading", "left", "like", "limit", "localtime", "localtimestamp", "natural", "not", "notnull", "null", "offset", "on", "only", "or", "order", "outer", "overlaps", "placing", "primary", "references", "returning", "right", "select", "session_user", "similar", "some", "symmetric", "table", "tablesample", "then", "to", "trailing", "true", "union", "unique", "user", "using", "variadic", "verbose", "when", "where", "window", "with"}
    integer_datatypes = {"bigint", "integer", "smallint", "int", "bigserial", "serial", "smallserial", "bigint generated always as identity", "bigint generated by default as identity"}
    for table_name, column_configs in tables.items():
        for col in column_configs:
            if not isinstance(col, dict): raise Exception(f"{table_name}: each column is a dict, got {col!r}")
            if removed := [key for key in col if key in COLUMN_KEYS_REMOVED]: raise Exception(f"{table_name}.{col.get('name')}: {removed[0]} removed in Atom 24.0.0: use {COLUMN_KEYS_REMOVED[removed[0]]}")
            if unknown := sorted(set(col) - set(COLUMN_KEYS)): raise Exception(f"{table_name}.{col.get('name')}: unknown key {', '.join(unknown)}; allowed: {', '.join(COLUMN_KEYS)}")
        for col in column_configs:    # id is optional; a key may span several columns (is_primary_key on each), or a table may have none
            if col.get("is_primary_key") is True and (extra := sorted(set(col) - {"name", "datatype", "identity", "is_primary_key"})):
                raise Exception(f"{table_name}.{col.get('name')} is a primary key column: it takes only name, datatype, identity and is_primary_key (not {', '.join(extra)})")
            if col.get("identity") is not None and (col.get("identity") not in ("always", "by_default") or col.get("is_primary_key") is not True or col.get("datatype") not in integer_datatypes):
                raise Exception(f"{table_name}.{col.get('name')}: identity ('always' or 'by_default') only on an integer primary key column")
            if col.get("name") == "id" and col.get("datatype") not in integer_datatypes:
                raise Exception(f"{table_name}.id must be an integer column (Atom's routes find rows by it)")
        column_names = set()
        for col in column_configs:
            col_name = col.get("name")
            if col_name:
                if col_name in column_names:
                    raise Exception(f"Duplicate column '{col_name}' defined in table '{table_name}'")
                column_names.add(col_name)
        for col in column_configs:
            name, dtype = col.get("name"), col.get("datatype")
            if not name or not dtype:
                raise Exception(f"Missing mandatory key 'name' or 'datatype' in {table_name} column: {col}")
            for key in ("is_primary_key", "is_not_null"):
                if key in col and not isinstance(col[key], bool):
                    raise Exception(f"{table_name}.{name} {key} must be True or False")
            for key in ("read_blocked", "write_blocked"):    # the route groups that may not read / write the column through Atom's table routes
                if key in col and (not isinstance(col[key], list) or not col[key] or any(group not in COLUMN_GROUPS for group in col[key]) or len(set(col[key])) != len(col[key])): raise Exception(f"{table_name}.{name}: {key} must be a list of {', '.join(COLUMN_GROUPS)} (each once; leave it out for none)")
            if "ownership" in col:    # the /my actions that may find a user's rows by this column (created_by_id always may)
                if name == "created_by_id": raise Exception(f"{table_name}.created_by_id: no ownership key; created_by_id is always the owner")
                if not isinstance(col["ownership"], list) or not col["ownership"] or any(action not in OWNERSHIP_ACTIONS for action in col["ownership"]) or len(set(col["ownership"])) != len(col["ownership"]): raise Exception(f"{table_name}.{name}: ownership must be a list of {', '.join(OWNERSHIP_ACTIONS)} (each once)")
            if "allowed_values" in col:    # a CHECK: the column holds only these values
                values = col["allowed_values"]
                if not isinstance(values, list) or not values or len(set(values)) != len(values) or not (all(isinstance(v, int) and not isinstance(v, bool) for v in values) or all(isinstance(v, str) for v in values)): raise Exception(f"{table_name}.{name}: allowed_values must be a list of integers or of texts, each once")
            if "int_mapping" in col:    # labels only (served by /info): never changes the database
                labels = col["int_mapping"]
                if dtype.lower().removesuffix("[]") not in integer_datatypes: raise Exception(f"{table_name}.{name}: int_mapping only on an integer column (or an integer array)")
                if not isinstance(labels, dict) or not labels or not all((code is None or (isinstance(code, int) and not isinstance(code, bool))) and isinstance(label, str) and label for code, label in labels.items()): raise Exception(f"{table_name}.{name}: int_mapping must be {{code: \"label\"}} with integer codes (None for no value)")
                if "allowed_values" in col and set(col["allowed_values"]) != {code for code in labels if code is not None}: raise Exception(f"{table_name}.{name}: allowed_values {col['allowed_values']} and int_mapping codes {[code for code in labels if code is not None]} must be the same")
            if name.lower() in reserved:
                raise Exception(f"Column name '{name}' in table '{table_name}' is a PostgreSQL reserved keyword. Please rename it.")
            if "generated" in col:
                if not isinstance(col["generated"], str) or not col["generated"].strip(): raise Exception(f"{table_name}.{name} generated must be the SQL expression of the column")
                if mixed := [key for key in ("default", "is_not_null", "allowed_values", "regex", "check", "unique", "old_name") if key in col]: raise Exception(f"{table_name}.{name} is generated: Postgres fills it, so it takes no {', '.join(mixed)}")
            if "old_name" in col and (not isinstance(col["old_name"], str) or not col["old_name"]): raise Exception(f"{table_name}.{name}: old_name must be the column's previous name")
            if "regex_message" in col and (not col.get("regex") or not isinstance(col["regex_message"], str) or not col["regex_message"]): raise Exception(f"{table_name}.{name}: regex_message is the error for its regex: a text, and the column needs regex")
            if "regex" in col:
                if not isinstance(col["regex"], str) or not col["regex"]: raise Exception(f"{table_name}.{name}: regex must be a pattern")
                if "'" in col["regex"]: raise Exception(f"{table_name}.{name}: regex may not contain a single quote")
                try: re.compile(col["regex"])
                except re.error as error: raise Exception(f"{table_name}.{name}: invalid regex: {error}") from None
            if "regex" in col and "[]" in dtype.lower():
                raise Exception(f"Regex constraint is not supported for array column {table_name}.{name}. Remove 'regex' key to resolve.")
            if "index" in col:
                if not isinstance(col["index"], list) or not col["index"] or not all(isinstance(item, str) and item.strip() for item in col["index"]): raise Exception(f"{table_name}.{name}: index must be a list of index texts, e.g. [\"btree(created_at)\", \"gin(tags)\"]")
                for index_group in (x.strip() for x in col["index"]):
                    if "|" in index_group: raise Exception(f"{table_name}.{name}: index is a list in Atom 24.0.0: one text per index, no |")
                    if "(" in index_group and index_group.endswith(")"):
                        index_type, cols_str = index_group[:-1].split("(", 1)
                        index_type = index_type.strip().lower()
                        index_cols = [c.strip() for c in cols_str.split(",")]
                        for ic in index_cols:
                            column, order = func_postgres_schema_index_column(token=ic)
                            if column not in column_names:
                                raise Exception(f"Index in {table_name} references non-existent column '{column}'. Defined: {list(column_names)}")
                            if order is None:
                                raise Exception(f"Index column '{ic}' in {table_name}: after the name only asc or desc, then nulls first or nulls last (btree(deviation_days desc nulls last,id))")
                            if order and index_type != "btree":
                                raise Exception(f"Index column '{ic}' in {table_name}: a sort direction only on btree indexes")
                        if (index_type == "hnsw") != dtype.lower().startswith("vector"):
                            raise Exception(f"{table_name}.{name}: a vector column takes an hnsw index, and hnsw only a vector column")
                        if index_type == "hnsw" and len(index_cols) != 1:
                            raise Exception(f"hnsw index on {table_name}.{name} takes one column")
                        if index_type == "gin":
                            if not any(x in dtype.lower() for x in ("[]", "jsonb", "text", "varchar", "tsvector")):
                                raise Exception(f"GIN index is not compatible with '{dtype}' on {table_name}.{name}. Supported: arrays, jsonb, text, varchar, tsvector.")
                        elif index_type == "gist":
                            if not any(x in dtype.lower() for x in ("geography", "geometry", "box", "circle", "point", "polygon")):
                                raise Exception(f"GIST index is not compatible with '{dtype}' on {table_name}.{name}. Supported: geography, geometry, spatial types.")
                        if any(x in dtype.lower() for x in ("geography", "geometry")) and index_type != "gist":
                            raise Exception(f"Spatial column {table_name}.{name} must use 'gist' index if indexed.")
                    else:
                        raise Exception(f"Invalid index syntax '{index_group}' in {table_name}.{name}. Expected 'type(col)' or 'type(col1,col2)'.")
        for col in column_configs:
            if "unique" in col:
                if not isinstance(col["unique"], list) or not col["unique"] or not all(isinstance(group, list) and group and all(isinstance(c, str) and c for c in group) for group in col["unique"]): raise Exception(f"{table_name}.{col['name']}: unique must be a list of column lists, e.g. [[\"email\", \"role\"]] or [[\"code\"]]")
                for group in col["unique"]:
                    for u_col in group:
                        if u_col not in column_names:
                            raise Exception(f"Unique constraint in {table_name} references non-existent column '{u_col}'. Defined columns: {list(column_names)}")
    return

def func_postgres_schema_users_setting(*, app_state: Any) -> dict:
    """The flat users setup switches read from app_state (config_is_root_user, config_is_users_password_log, config_is_users_delete_log, config_is_totp_clear); one not set is on."""
    return {key: getattr(app_state, key, True) for key in ("config_is_root_user", "config_is_users_password_log", "config_is_users_delete_log", "config_is_totp_clear")}

def func_postgres_schema_context_build(*, config_postgres_schema: dict, users_setting: dict = None) -> dict:
    """The switches and row guards of one schema's control, the managed-object catalog, and the users setup switches (users_setting: config_is_root_user, config_is_users_password_log, config_is_users_delete_log, config_is_totp_clear; all on when not given)."""
    control = config_postgres_schema.get("control") or {}
    catalog = {"idx": set(), "uni": set(), "chk": set(), "tg": set()}
    def register_sql_catalog(sql_config: Any) -> None:
        if not isinstance(sql_config, dict): return
        for key, val in sql_config.items():
            if isinstance(key, str) and isinstance(val, str):
                if key.startswith("index_"): catalog["idx"].add(key[6:])
                elif key.startswith("idx_"): catalog["idx"].add(key)
                elif key.startswith("unique_"): catalog["uni"].add(key)
                elif key.startswith("check_"): catalog["chk"].add(key)
            elif isinstance(val, dict): register_sql_catalog(val)
        return
    register_sql_catalog(config_postgres_schema.get("sql", {}))
    users = {"config_is_root_user": True, "config_is_users_password_log": True, "config_is_users_delete_log": True, "config_is_totp_clear": True, **(users_setting or {})}
    return {"catalog": catalog, "tables": set(config_postgres_schema.get("table") or {}), **{key: control.get(key, default) for key, default in CONTROL_SWITCHES.items()},
            "is_root_user": bool(users["config_is_root_user"]), "is_users_password_log": bool(users["config_is_users_password_log"]), "is_users_delete_log": bool(users["config_is_users_delete_log"]), "is_totp_clear": bool(users["config_is_totp_clear"]),
            "bulk_blocked": [[name, number] for name, number in (control.get("row_delete_max") or {}).items()], "update_blocked": list(control.get("row_update_disabled") or []), "table_blocked": list(control.get("row_delete_disabled") or [])}

def func_postgres_schema_hash(value: Any) -> str:
    """Return the stable short hash used in managed PostgreSQL object names."""
    return hashlib.md5(str(value).encode(), usedforsecurity=False).hexdigest()[:4]

def func_postgres_schema_identifier(name: str) -> str:
    """Clamp a managed PostgreSQL identifier to PostgreSQL's 63-byte naming convention."""
    if len(name) <= 63: return name
    return f"{name[:58]}_{func_postgres_schema_hash(name)}"

INDEX_ORDERS = ("", "ASC", "DESC", "ASC NULLS FIRST", "ASC NULLS LAST", "DESC NULLS FIRST", "DESC NULLS LAST", "NULLS FIRST", "NULLS LAST")

def func_postgres_schema_index_column(*, token: str) -> tuple:
    """(column, order) of one index column token: "deviation_days desc nulls last" -> ("deviation_days", "DESC NULLS LAST"); order is "" when none and None when it is not a valid sort order."""
    column, *words = token.split()
    order = " ".join(words).upper()
    return column, order if order in INDEX_ORDERS else None

def func_postgres_schema_col_setting_enabled(col_cfg: dict, key: str) -> bool:
    """Return whether an optional column setting has a usable configured value."""
    return key in col_cfg and col_cfg.get(key) not in (None, "")

def func_postgres_schema_sql_queries(sql_config: Any):
    """Yield custom SQL strings from nested mapping and sequence configuration."""
    if isinstance(sql_config, dict):
        for val in sql_config.values(): yield from func_postgres_schema_sql_queries(val)
    elif isinstance(sql_config, (list, tuple)):
        for val in sql_config: yield from func_postgres_schema_sql_queries(val)
    elif isinstance(sql_config, str) and sql_config.strip(): yield sql_config

async def func_postgres_schema_extensions_init(*, conn: asyncpg.Connection, extensions: list) -> None:
    """Install the configured PostgreSQL extensions that are missing. Every one is optional: one this server lacks or this user may not install is skipped with a warning, never stopping startup; a column that needs it stops startup instead (func_postgres_schema_types_check)."""
    if not extensions: return
    rows = await conn.fetch("SELECT name, installed_version FROM pg_available_extensions WHERE name = ANY($1::text[])", list(extensions))
    available, installed = {r[0] for r in rows}, {r[0] for r in rows if r[1]}
    for extension in extensions:
        if extension in installed: continue
        if extension not in available:
            print(f"⚠️  {f'extension {extension}':<30} : ❌ skipped (not on this server)")
            continue
        try: await conn.execute(f'CREATE EXTENSION IF NOT EXISTS "{extension}";')
        except Exception as e: print(f"⚠️  {f'extension {extension}':<30} : ❌ skipped ({str(e).splitlines()[0][:120]})")
    return

EXTENSION_TYPES = {"vector": "vector", "geography": "postgis", "geometry": "postgis"}

async def func_postgres_schema_types_check(*, conn: asyncpg.Connection, tables: dict) -> None:
    """Before any table changes: a column whose datatype comes from an extension (vector, geography, geometry) needs that extension installed, else startup stops naming the column and the extension."""
    needed = {}
    for table_name, column_configs in tables.items():
        for col in column_configs:
            base = str(col.get("datatype", "")).lower().split("(")[0].replace("[]", "").strip()
            if base in EXTENSION_TYPES: needed.setdefault(base, f"{table_name}.{col['name']}")
    for base, column in needed.items():
        if await conn.fetchval("SELECT to_regtype($1) IS NULL", base): raise Exception(f"{column} is a {base} column: it needs the PostgreSQL extension {EXTENSION_TYPES[base]}, which this database doesn't have (add it to control.extension of that database's config_postgres_schema_<name>, or install it: CREATE EXTENSION {EXTENSION_TYPES[base]})")
    return

async def func_postgres_schema_tables_sync(*, conn: asyncpg.Connection, tables: dict, catalog: dict) -> None:
    """Synchronize configured tables, columns, indexes, and constraints: the current state is read once for all tables, then only what differs is changed."""
    await func_postgres_schema_types_check(conn=conn, tables=tables)
    names = list(tables)
    existing_tables = {r[0] for r in await conn.fetch("SELECT c.relname FROM pg_class c JOIN pg_namespace n ON c.relnamespace = n.oid WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p') AND c.relname = ANY($1::text[])", names)}
    for table_name in names:
        if table_name in existing_tables: continue
        primary_cols = [col for col in tables[table_name] if col.get("is_primary_key") is True]    # created with the table: one key over all of them; none, a table without a key
        definitions = [f'"{col["name"]}" {col["datatype"]}' + (f" GENERATED {col['identity'].upper().replace('_', ' ')} AS IDENTITY" if col.get("identity") else "") for col in primary_cols]
        if primary_cols: definitions.append(f"PRIMARY KEY ({', '.join(chr(34) + col['name'] + chr(34) for col in primary_cols)})")
        await conn.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(definitions)});')
    column_rows = await conn.fetch("SELECT t.relname, a.attname, format_type(a.atttypid, a.atttypmod) as type, a.attnotnull as notnull, pg_get_expr(ad.adbin, ad.adrelid) as default, a.attgenerated = 's' AS generated, col_description(t.oid, a.attnum) AS comment FROM pg_attribute a JOIN pg_class t ON a.attrelid = t.oid JOIN pg_namespace n ON t.relnamespace = n.oid LEFT JOIN pg_attrdef ad ON a.attrelid = ad.adrelid AND a.attnum = ad.adnum WHERE t.relname = ANY($1::text[]) AND n.nspname = 'public' AND a.attnum > 0 AND NOT a.attisdropped", names)
    meta_rows = await conn.fetch("SELECT tablename, indexname FROM pg_indexes WHERE schemaname = 'public' AND tablename = ANY($1::text[]) UNION ALL SELECT t.relname, con.conname FROM pg_constraint con JOIN pg_class t ON con.conrelid = t.oid JOIN pg_namespace n ON t.relnamespace = n.oid WHERE n.nspname = 'public' AND t.relname = ANY($1::text[])", names)
    for table_name, column_configs in tables.items():
        rows = [r[1:] for r in column_rows if r[0] == table_name]
        current_cols = {r[0]: r[1] for r in rows}
        current_notnulls = {r[0]: r[2] for r in rows}
        current_defaults = {r[0]: r[3] for r in rows}
        current_generated = {r[0]: r[4] for r in rows}
        current_comments = {r[0]: r[5] for r in rows}
        existing_meta = {r[1] for r in meta_rows if r[0] == table_name}
        table_changed = False
        renamed_cols = {}
        for col_cfg in column_configs:
            if col_cfg.get("is_primary_key") is True:
                continue
            col_name = col_cfg["name"]
            col_type = col_cfg["datatype"]
            if col_cfg.get("generated"):
                # a generated column (Postgres fills it from other columns): marked with its expression's hash, rebuilt when the expression changes; it holds no data of its own
                marker = f"atom generated {func_postgres_schema_hash(col_cfg['generated'])}"
                if col_name in current_cols:
                    if current_comments.get(col_name) == marker: continue
                    if not current_generated.get(col_name): raise Exception(f"{table_name}.{col_name} is a plain column with data: rename it (old) or drop it before it becomes generated")
                    await conn.execute(f'ALTER TABLE "{table_name}" DROP COLUMN "{col_name}"')
                    existing_meta = {r[0] for r in await conn.fetch("SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND tablename = $1 UNION ALL SELECT con.conname FROM pg_constraint con JOIN pg_class t ON con.conrelid = t.oid JOIN pg_namespace n ON t.relnamespace = n.oid WHERE n.nspname = 'public' AND t.relname = $1", table_name)}
                await conn.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type} GENERATED ALWAYS AS ({col_cfg["generated"]}) STORED')
                await conn.execute(f"COMMENT ON COLUMN \"{table_name}\".\"{col_name}\" IS '{marker}'")
                current_cols[col_name] = col_type
                table_changed = True
                continue
            if col_name not in current_cols:
                old_name = col_cfg.get("old_name") or None
                if old_name and old_name in current_cols:
                    await conn.execute(f'ALTER TABLE "{table_name}" RENAME COLUMN "{old_name}" TO "{col_name}"')
                    current_cols[col_name] = current_cols.pop(old_name)
                    current_notnulls[col_name] = current_notnulls.pop(old_name)
                    renamed_cols[col_name] = old_name
                    table_changed = True
                else:
                    default_val = f"""DEFAULT {col_cfg["default"]}""" if func_postgres_schema_col_setting_enabled(col_cfg, "default") else ""
                    mandatory_val = "NOT NULL" if col_cfg.get("is_not_null") is True else ""
                    await conn.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type} {default_val} {mandatory_val}')
                    current_cols[col_name] = col_type.split("(")[0].lower()
                    current_notnulls[col_name] = col_cfg.get("is_not_null") is True
                    table_changed = True
            else:
                # one name per type: Postgres reports full names (format_type), config may use either, and a mismatch would rewrite the table on every start
                type_map = {"timestamp with time zone": "timestamptz", "timestamp without time zone": "timestamp", "time with time zone": "timetz", "time without time zone": "time",
                            "character varying": "varchar", "character": "char", "bpchar": "char", "integer": "int", "int4": "int", "int8": "bigint", "int2": "smallint",
                            "boolean": "bool", "double precision": "float8", "float": "float8", "real": "float4", "decimal": "numeric", "bit varying": "varbit"}
                current_type = type_map.get(current_cols[col_name].lower().split("(")[0], current_cols[col_name].lower().split("(")[0])
                target_type = type_map.get(col_type.lower().split("(")[0], col_type.lower().split("(")[0])
                if current_type != target_type:
                    await conn.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN "{col_name}" TYPE {col_type} USING "{col_name}"::{col_type}')
                    table_changed = True
                target_notnull = col_cfg.get("is_not_null") is True
                if current_notnulls[col_name] != target_notnull:
                    if target_notnull:
                        await conn.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN "{col_name}" SET NOT NULL')
                    else:
                        await conn.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN "{col_name}" DROP NOT NULL')
                    table_changed = True
                target_default = str(col_cfg.get("default")).strip() if func_postgres_schema_col_setting_enabled(col_cfg, "default") else None
                current_default = current_defaults.get(col_name)
                if target_default:
                    if current_default is None or target_default not in current_default:
                         await conn.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN "{col_name}" SET DEFAULT {target_default}')
                         table_changed = True
                elif current_default is not None:
                    await conn.execute(f'ALTER TABLE "{table_name}" ALTER COLUMN "{col_name}" DROP DEFAULT')
                    table_changed = True
        for col_cfg in column_configs:
            if col_cfg.get("is_primary_key") is True:
                continue
            col_name = col_cfg["name"]
            col_type = col_cfg["datatype"]
            if col_cfg.get("index"):
                for index_group in (x.strip() for x in col_cfg["index"]):
                    if "(" in index_group and index_group.endswith(")"):
                        index_type, cols_str = index_group[:-1].split("(", 1)
                        index_type = index_type.strip().lower()
                        index_cols = [c.strip() for c in cols_str.split(",")]
                        idx_name = func_postgres_schema_identifier(f"idx_{table_name}_{'_'.join(c.replace(' ', '_') for c in index_cols)}_{index_type}")
                        catalog["idx"].add(idx_name)
                        if idx_name not in existing_meta:
                            # access method + operator class derived from the explicit token
                            access_method, opclass = {"gin_trgm": ("gin", "gin_trgm_ops"), "hnsw": ("hnsw", "vector_cosine_ops")}.get(index_type, (index_type, None))
                            if opclass:
                                await conn.execute(f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON "{table_name}" USING {access_method}("{index_cols[0]}" {opclass});')
                            else:
                                cols_quoted = ", ".join(f'"{column}"' + (f" {order}" if order else "") for column, order in (func_postgres_schema_index_column(token=c) for c in index_cols))
                                await conn.execute(f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON "{table_name}" USING {access_method}({cols_quoted});')
                            table_changed = True
            if col_cfg.get("allowed_values"):    # named by the hash of the values as a tuple, so the name stays as it was when the key was in (a tuple)
                allowed = tuple(col_cfg["allowed_values"])
                chk_name = f"check_{table_name}_{col_name}_in_{func_postgres_schema_hash(allowed)}"
                catalog["chk"].add(chk_name)
                if chk_name not in existing_meta:
                    old_col_name = renamed_cols.get(col_name, col_name)
                    old_chk_name = f"check_{table_name}_{old_col_name}_in_{func_postgres_schema_hash(allowed)}"
                    if old_chk_name in existing_meta and old_chk_name != chk_name:
                        await conn.execute(f'ALTER TABLE "{table_name}" RENAME CONSTRAINT "{old_chk_name}" TO "{chk_name}"')
                        existing_meta.remove(old_chk_name)
                        existing_meta.add(chk_name)
                    else:
                        await conn.execute(f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{chk_name}" CHECK ("{col_name}" IN ({", ".join(str(v) if isinstance(v, int) else "'" + v.replace("'", "''") + "'" for v in allowed)}));')
                        table_changed = True
            if func_postgres_schema_col_setting_enabled(col_cfg, "regex") and (table_name, col_name) != ("users", "password"):    # the stored password is its hash: the API checks the typed one
                regex_name = f"check_{table_name}_{col_name}_regex_{func_postgres_schema_hash(col_cfg['regex'])}"
                catalog["chk"].add(regex_name)
                if regex_name not in existing_meta:
                    old_col_name = renamed_cols.get(col_name, col_name)
                    old_regex_name = f"check_{table_name}_{old_col_name}_regex_{func_postgres_schema_hash(col_cfg['regex'])}"
                    if old_regex_name in existing_meta and old_regex_name != regex_name:
                        await conn.execute(f'ALTER TABLE "{table_name}" RENAME CONSTRAINT "{old_regex_name}" TO "{regex_name}"')
                        existing_meta.remove(old_regex_name)
                        existing_meta.add(regex_name)
                    else:
                        await conn.execute(f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{regex_name}" CHECK ("{col_name}" ~ \'{col_cfg["regex"]}\');')
                        table_changed = True
            if func_postgres_schema_col_setting_enabled(col_cfg, "check"):
                vld_name = f"check_{table_name}_{col_name}_vld_{func_postgres_schema_hash(col_cfg['check'])}"
                catalog["chk"].add(vld_name)
                if vld_name not in existing_meta:
                    old_col_name = renamed_cols.get(col_name, col_name)
                    old_vld_name = f"check_{table_name}_{old_col_name}_vld_{func_postgres_schema_hash(col_cfg['check'])}"
                    if old_vld_name in existing_meta and old_vld_name != vld_name:
                        await conn.execute(f'ALTER TABLE "{table_name}" RENAME CONSTRAINT "{old_vld_name}" TO "{vld_name}"')
                        existing_meta.remove(old_vld_name)
                        existing_meta.add(vld_name)
                    else:
                        await conn.execute(f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{vld_name}" CHECK ({col_cfg["check"]});')
                        table_changed = True
            if col_cfg.get("unique"):
                for group in col_cfg["unique"]:
                    unique_cols = [x.strip() for x in group]
                    uni_name = f"""unique_{table_name}_{"_".join(unique_cols)}"""
                    catalog["uni"].add(uni_name)
                    if uni_name not in existing_meta:
                        old_unique_cols = [renamed_cols.get(c, c) for c in unique_cols]
                        old_uni_name = f"""unique_{table_name}_{"_".join(old_unique_cols)}"""
                        if old_uni_name in existing_meta and old_uni_name != uni_name:
                            await conn.execute(f'ALTER TABLE "{table_name}" RENAME CONSTRAINT "{old_uni_name}" TO "{uni_name}"')
                            existing_meta.remove(old_uni_name)
                            existing_meta.add(uni_name)
                        else:
                            cols_quoted = ",".join([f'"{x}"' for x in unique_cols])
                            await conn.execute(f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{uni_name}" UNIQUE ({cols_quoted});')
                            table_changed = True
        if table_changed:
            await conn.execute(f'ANALYZE "{table_name}";')
    return

async def func_postgres_schema_tables_read(*, conn: asyncpg.Connection) -> dict:
    """Read public base-table columns needed by trigger and user setup."""
    db_schema_rows = await conn.fetch("SELECT c.table_name, c.column_name FROM information_schema.columns c JOIN information_schema.tables t ON c.table_name = t.table_name AND c.table_schema = t.table_schema WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE'")
    db_tables = {}
    for row in db_schema_rows:
        db_tables.setdefault(row[0], []).append(row[1])
    return db_tables

async def func_postgres_schema_triggers_read(*, conn: asyncpg.Connection) -> dict:
    """Read every trigger on public tables with its definition, keyed by (table, trigger name)."""
    rows = await conn.fetch("SELECT c.relname, t.tgname, pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON t.tgrelid = c.oid JOIN pg_namespace n ON c.relnamespace = n.oid WHERE n.nspname = 'public' AND NOT t.tgisinternal")
    return {(r[0], r[1]): r[2] for r in rows}

async def func_postgres_schema_trigger_set(*, conn: asyncpg.Connection, existing: dict, table: str, name: str, definition: str) -> None:
    """Create a trigger unless the same definition is already there; inside schema init's transaction the drop and create are atomic, so a guard never disappears for other sessions."""
    def normalize(sql): return " ".join(str(sql).lower().replace("public.", "").replace('"', "").replace("'", "").rstrip(";").split())
    if normalize(existing.get((table, name), "")) == normalize(f"CREATE TRIGGER {name} {definition}"): return
    await conn.execute(f"DROP TRIGGER IF EXISTS {name} ON {table}; CREATE TRIGGER {name} {definition};")
    existing[(table, name)] = f"CREATE TRIGGER {name} {definition}"

async def func_postgres_schema_users_init(*, conn: asyncpg.Connection, db_tables: dict, catalog: dict, context: dict, root_user_password_hash: str = None) -> None:
    """Initialize root-user protection, root credentials, user audit triggers and the two-factor clear trigger (config_is_totp_clear) (root's permissions: func_root_user_permissions_sync, at every start)."""
    is_root_user = context.get("is_root_user", True)    # config_is_root_user: create admin (id 1, role 1) and guard it from delete
    is_root_user_delete_disabled = is_root_user_create = is_root_user
    is_log_users_password = context.get("is_users_password_log", True)
    is_log_users_delete = context.get("is_users_delete_log", True)
    users_cols = db_tables.get("users", []) if context.get("database", "master") == "master" and "users" in context.get("tables", {"users"}) else []    # login users live in master only: a users table in another database is a plain table
    existing = context["triggers"] if "triggers" in context else await func_postgres_schema_triggers_read(conn=conn)
    if users_cols:
        is_log_password = is_log_users_password and "password" in users_cols and "log_users_password" in db_tables
        is_log_delete = is_log_users_delete and "deleted_at" in users_cols and "log_users_delete" in db_tables
        functions = [sql for sql, is_on in (("CREATE OR REPLACE FUNCTION func_protect_root_users() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF TG_OP = 'DELETE' THEN IF OLD.id = 1 THEN RAISE EXCEPTION 'DELETE not allowed for root user (id=1)'; END IF; RETURN OLD; END IF; RETURN NULL; END; $$;", is_root_user_delete_disabled), ('CREATE OR REPLACE FUNCTION func_password_log_users() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.password IS DISTINCT FROM NEW.password THEN INSERT INTO log_users_password (user_id, password, created_by_id) VALUES (NEW.id, NEW.password, NEW.updated_by_id); END IF; RETURN NEW; END; $$;', is_log_password), ("CREATE OR REPLACE FUNCTION func_log_users_delete() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF TG_OP = 'UPDATE' THEN IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN INSERT INTO log_users_delete (user_id, type, created_by_id) VALUES (NEW.id, 1, COALESCE(NEW.deleted_by_id, NEW.updated_by_id)); ELSIF OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS NULL THEN INSERT INTO log_users_delete (user_id, type, created_by_id) VALUES (NEW.id, 2, NEW.updated_by_id); END IF; RETURN NEW; ELSIF TG_OP = 'DELETE' THEN INSERT INTO log_users_delete (user_id, type) VALUES (OLD.id, 3); RETURN OLD; END IF; RETURN NULL; END; $$;", is_log_delete)) if is_on]
        if functions: await conn.execute(" ".join(functions))    # one round trip for the trigger functions
        if is_root_user_delete_disabled:
            catalog["tg"].add("trigger_protect_root_users")
            await func_postgres_schema_trigger_set(conn=conn, existing=existing, table="users", name="trigger_protect_root_users", definition="BEFORE DELETE ON users FOR EACH ROW EXECUTE FUNCTION func_protect_root_users()")
        if is_root_user_create and all(c in users_cols for c in ("username", "password", "role", "deleted_at", "deactivated_at")):
            if not root_user_password_hash:
                raise Exception("config_root_user_password must be set in .env when config_is_root_user is on")
            await conn.execute("INSERT INTO users (username, password, role) VALUES ('admin', $1, 1) ON CONFLICT (username, role) DO UPDATE SET username = 'admin', password = EXCLUDED.password, role = 1, deleted_at = NULL, deactivated_at = NULL;", root_user_password_hash)
            await conn.execute("UPDATE users SET username = 'admin', password = $1, role = 1, deleted_at = NULL, deactivated_at = NULL WHERE id = 1;", root_user_password_hash)
        if is_log_password:
            catalog["tg"].add("trigger_password_log_users")
            await func_postgres_schema_trigger_set(conn=conn, existing=existing, table="users", name="trigger_password_log_users", definition="AFTER UPDATE ON users FOR EACH ROW EXECUTE FUNCTION func_password_log_users()")
        if is_log_delete:
            catalog["tg"].add("trigger_log_users_delete")
            await func_postgres_schema_trigger_set(conn=conn, existing=existing, table="users", name="trigger_log_users_delete", definition="AFTER DELETE OR UPDATE OF deleted_at ON users FOR EACH ROW EXECUTE FUNCTION func_log_users_delete()")
        if context.get("is_totp_clear", True) and all(c in users_cols for c in ("totp_enabled_at", "totp_secret", "totp_last_step", "totp_recovery")):    # two-factor turned off: its secret, last step and recovery codes go with it
            await conn.execute("CREATE OR REPLACE FUNCTION users_totp_clear() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.totp_enabled_at IS NULL AND OLD.totp_enabled_at IS NOT NULL THEN NEW.totp_secret = NULL; NEW.totp_last_step = NULL; NEW.totp_recovery = NULL; END IF; RETURN NEW; END $$;")
            catalog["tg"].add("users_totp_clear")
            await func_postgres_schema_trigger_set(conn=conn, existing=existing, table="users", name="users_totp_clear", definition="BEFORE UPDATE OF totp_enabled_at ON users FOR EACH ROW EXECUTE FUNCTION users_totp_clear()")
    return

async def func_postgres_schema_triggers_sync(*, conn: asyncpg.Connection, db_tables: dict, catalog: dict, context: dict) -> None:
    """Synchronize generic and table-specific protection/update triggers."""
    is_truncate_disabled = context.get("is_truncate_disabled", True)
    is_protected_delete_disabled = context["is_protected_delete_disabled"]
    is_updated_at_set = context["is_updated_at_set"]
    bulk_blocked = context["bulk_blocked"]
    table_blocked = context["table_blocked"]
    update_blocked = context.get("update_blocked", [])
    existing = context["triggers"] if "triggers" in context else await func_postgres_schema_triggers_read(conn=conn)
    await conn.execute("CREATE OR REPLACE FUNCTION func_delete_disable_is_protected() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF OLD.is_protected IS TRUE THEN RAISE EXCEPTION 'DELETE not allowed for protected row in %', TG_TABLE_NAME; END IF; RETURN OLD; END; $$; CREATE OR REPLACE FUNCTION func_set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN NEW.updated_at=NOW(); RETURN NEW; END; $$; CREATE OR REPLACE FUNCTION func_set_updated_at_except_activity() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF to_jsonb(NEW) - 'updated_at' - 'last_active_at' IS DISTINCT FROM to_jsonb(OLD) - 'updated_at' - 'last_active_at' THEN NEW.updated_at=NOW(); END IF; RETURN NEW; END; $$; CREATE OR REPLACE FUNCTION func_delete_disable_bulk() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE n BIGINT := TG_ARGV[0]; BEGIN IF (SELECT COUNT(*) FROM deleted_rows) > n THEN RAISE EXCEPTION 'cant delete more than % rows',n; END IF; RETURN OLD; END; $$; CREATE OR REPLACE FUNCTION func_delete_disable_table() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'operation not allowed on %', TG_TABLE_NAME; END; $$;")
    managed = context.get("tables")
    for table, cols in db_tables.items():
        if table == "spatial_ref_sys" or (managed is not None and table not in managed): continue    # only the tables of this database's schema
        if is_truncate_disabled:
            trunc_tg_name = f"trigger_truncate_disable_{table}"
            catalog["tg"].add(trunc_tg_name)
            await func_postgres_schema_trigger_set(conn=conn, existing=existing, table=table, name=trunc_tg_name, definition=f"BEFORE TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION func_delete_disable_table()")
        if is_protected_delete_disabled and "is_protected" in cols:
            prot_tg_name = f"trigger_delete_disable_is_protected_{table}"
            catalog["tg"].add(prot_tg_name)
            await func_postgres_schema_trigger_set(conn=conn, existing=existing, table=table, name=prot_tg_name, definition=f"BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION func_delete_disable_is_protected()")
        if is_updated_at_set and "updated_at" in cols:
            upd_tg_name = f"trigger_updated_at_set_{table}"
            catalog["tg"].add(upd_tg_name)
            await func_postgres_schema_trigger_set(conn=conn, existing=existing, table=table, name=upd_tg_name, definition=f"BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION {'func_set_updated_at_except_activity' if 'last_active_at' in cols else 'func_set_updated_at'}()")    # recording activity (last_active_at) is not an edit
    for table, limit in bulk_blocked:
        if table in db_tables:
            bulk_tg_name = f"trigger_delete_disable_bulk_{table}"
            catalog["tg"].add(bulk_tg_name)
            await func_postgres_schema_trigger_set(conn=conn, existing=existing, table=table, name=bulk_tg_name, definition=f"AFTER DELETE ON {table} REFERENCING OLD TABLE AS deleted_rows FOR EACH STATEMENT EXECUTE FUNCTION func_delete_disable_bulk('{limit}')")
    for table in table_blocked:
        if table in db_tables:
            tab_tg_name = f"trigger_delete_disable_{table}"
            catalog["tg"].add(tab_tg_name)
            await func_postgres_schema_trigger_set(conn=conn, existing=existing, table=table, name=tab_tg_name, definition=f"BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION func_delete_disable_table()")
    for table in update_blocked:    # append-only tables: the database refuses every UPDATE, whoever sends it (admin SQL runner, scripts)
        if table in db_tables:
            upd_block_tg_name = f"trigger_update_disable_{table}"
            catalog["tg"].add(upd_block_tg_name)
            await func_postgres_schema_trigger_set(conn=conn, existing=existing, table=table, name=upd_block_tg_name, definition=f"BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION func_delete_disable_table()")
    return

async def func_postgres_schema_cleanup(*, conn: asyncpg.Connection, tables: dict, catalog: dict) -> None:
    """Remove obsolete generated triggers, constraints, and indexes from managed tables."""
    managed_tables = list(tables.keys())
    managed_tables_str = ",".join(f"'{t}'" for t in managed_tables) if managed_tables else "''"
    blocks = []    # one statement for all three, a single round trip
    for prefix in ("tg", "uni_chk", "idx"):
        wants = catalog["tg"] if prefix == "tg" else catalog["uni"] | catalog["chk"] if prefix == "uni_chk" else catalog["idx"] | catalog["uni"] | catalog["chk"]
        wants_str = ",".join(f"'{i}'" for i in wants) if wants else "''"
        if prefix == "idx":
            selection = "indexname"
            info_tbl = "pg_indexes"
            join_clause = ""
            drop_fmt = "DROP INDEX IF EXISTS %I"
            drop_vars = "record.indexname"
            like_filter = f"(indexname LIKE 'idx_%%' OR indexname LIKE 'unique_%%' OR indexname LIKE 'check_%%') AND tablename IN ({managed_tables_str})"
        elif prefix == "tg":
            selection = "tgname, relname"
            info_tbl = "pg_trigger"
            join_clause = "JOIN pg_class ON pg_trigger.tgrelid = pg_class.oid"
            drop_fmt = "DROP TRIGGER IF EXISTS %I ON %I"
            drop_vars = "record.tgname, record.relname"
            like_filter = f"tgname LIKE 'trigger_%%' AND relname IN ({managed_tables_str})"
        else:
            selection = "conname, relname"
            info_tbl = "pg_constraint"
            join_clause = "JOIN pg_class ON pg_constraint.conrelid = pg_class.oid"
            drop_fmt = "ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I"
            drop_vars = "record.relname, record.conname"
            like_filter = f"(conname LIKE 'unique_%%' OR conname LIKE 'check_%%') AND relname IN ({managed_tables_str})"
        blocks.append(f"""DO $$ DECLARE record RECORD; BEGIN FOR record IN SELECT {selection} FROM {info_tbl} {join_clause} WHERE {like_filter} LOOP IF NOT record.{selection.split(",")[0]} IN ({wants_str}) THEN EXECUTE format('{drop_fmt}', {drop_vars}); END IF; END LOOP; END $$;""")  # noqa: S608 - table names come from config_postgres_schema, not requests
    await conn.execute(" ".join(blocks))
    return

async def func_postgres_schema_sql_execute(*, conn: asyncpg.Connection, sql_config: Any) -> None:
    """Execute configured custom SQL after managed schema synchronization."""
    for query in func_postgres_schema_sql_queries(sql_config): await conn.execute(query)
    return

async def func_postgres_schema_lock_timeout(*, conn: Any, lock_timeout_sec: int) -> Any:
    """Inside the schema transaction: wait at most lock_timeout_sec for each table lock, so a busy table makes startup fail with a clear message instead of hanging the deploy."""
    if lock_timeout_sec: await conn.execute(f"SET LOCAL lock_timeout = '{int(lock_timeout_sec)}s'")
    return

def func_postgres_schema_lock_error(*, error: Exception, lock_timeout_sec: int) -> Exception:
    return Exception(f"schema init: a table stayed locked by other sessions for over {lock_timeout_sec} s (config_postgres_lock_timeout_sec), so nothing was changed; start again when it is quiet. See what would change: venv/bin/python -m script.postgres_schema_plan ({error})")

async def func_postgres_schema_tables_init(*, app_state: State, client_postgres: asyncpg.Pool, tables: dict, lock_timeout_sec: int = 10) -> str:
    """Create or update only the given tables ({name: {"column": [...]}}) (columns, indexes, constraints); no extensions, users or triggers, so other tables in that database are untouched."""
    config_postgres_schema = {"table": tables}
    app_state.func_postgres_schema_config_validate(config_postgres_schema=config_postgres_schema)
    context = app_state.func_postgres_schema_context_build(config_postgres_schema=config_postgres_schema)
    try:
        async with client_postgres.acquire() as conn, conn.transaction():
            await func_postgres_schema_lock_timeout(conn=conn, lock_timeout_sec=lock_timeout_sec)
            await app_state.func_postgres_schema_tables_sync(conn=conn, tables=func_postgres_schema_columns(config_postgres_schema=config_postgres_schema), catalog=context["catalog"])
    except asyncpg.exceptions.LockNotAvailableError as e: raise func_postgres_schema_lock_error(error=e, lock_timeout_sec=lock_timeout_sec) from None
    return "tables init done"

async def func_postgres_schema_steps(*, app_state: State, conn: Any, config_postgres_schema: dict, context: dict, root_user_password_hash: str = None, lock_timeout_sec: int = 10) -> None:
    """The schema steps, in order, on one connection: startup runs them for real, func_postgres_schema_plan only records their statements."""
    # extensions outside the transaction: each is optional, and one skipped must not abort the rest
    await app_state.func_postgres_schema_extensions_init(conn=conn, extensions=(config_postgres_schema.get("control") or {}).get("extension") or [])
    # one transaction: other sessions see the old schema or the new one, never a table without its triggers
    async with conn.transaction():
        await func_postgres_schema_lock_timeout(conn=conn, lock_timeout_sec=lock_timeout_sec)
        await app_state.func_postgres_schema_tables_sync(conn=conn, tables=func_postgres_schema_columns(config_postgres_schema=config_postgres_schema), catalog=context["catalog"])
        db_tables = await app_state.func_postgres_schema_tables_read(conn=conn)
        context["triggers"] = await app_state.func_postgres_schema_triggers_read(conn=conn)
        await app_state.func_postgres_schema_users_init(conn=conn, db_tables=db_tables, catalog=context["catalog"], context=context, root_user_password_hash=root_user_password_hash)
        await app_state.func_postgres_schema_triggers_sync(conn=conn, db_tables=db_tables, catalog=context["catalog"], context=context)
        await app_state.func_postgres_schema_cleanup(conn=conn, tables=config_postgres_schema.get("table") or {}, catalog=context["catalog"])
    # custom SQL last and outside the transaction, as before (it may hold statements such as CREATE INDEX CONCURRENTLY)
    await app_state.func_postgres_schema_sql_execute(conn=conn, sql_config=config_postgres_schema.get("sql", {}))
    return

async def func_postgres_schema_init(*, app_state: State, client_postgres: asyncpg.Pool | None, config_postgres_schema: dict, root_user_password_hash: str = None, lock_timeout_sec: int = 10, database: str = "master") -> str:
    """Initialize PostgreSQL schema by composing focused helpers registered on app.state; database: its name (the users setup runs on master only)."""
    app_state.func_postgres_schema_config_validate(config_postgres_schema=config_postgres_schema)
    context = {**app_state.func_postgres_schema_context_build(config_postgres_schema=config_postgres_schema, users_setting=func_postgres_schema_users_setting(app_state=app_state)), "database": database}
    try:
        async with client_postgres.acquire() as conn: await func_postgres_schema_steps(app_state=app_state, conn=conn, config_postgres_schema=config_postgres_schema, context=context, root_user_password_hash=root_user_password_hash, lock_timeout_sec=lock_timeout_sec)
    except asyncpg.exceptions.LockNotAvailableError as e: raise func_postgres_schema_lock_error(error=e, lock_timeout_sec=lock_timeout_sec) from None
    return "database init done"

async def func_postgres_schema_check(*, app_state: State, client_postgres: asyncpg.Pool, config_postgres_schema: dict, name: str = "master") -> str:
    """Startup with config_is_postgres_schema_init off: compare the database with config_postgres_schema, change nothing, and stop when they differ, so the app never runs against a schema its code does not expect."""
    changes = [step["sql"] for step in await app_state.func_postgres_schema_plan(app_state=app_state, client_postgres=client_postgres, config_postgres_schema=config_postgres_schema, database=name) if not step["is_routine"]]
    if changes:
        preview = "; ".join(" ".join(sql.split()).rstrip(";")[:120] for sql in changes[:3]) + ("; …" if len(changes) > 3 else "")
        raise Exception(f"schema check: database {name} differs from config_postgres_schema_{name} ({len(changes)} changes) and config_is_postgres_schema_init is off, so nothing was changed. See them: venv/bin/python -m script.postgres_schema_plan; run them: venv/bin/python -m script.postgres_schema_plan --apply ({preview})")
    return "schema check done"

SCHEMA_RISKS = ((r"ALTER COLUMN .* TYPE ", "rewrites the table, which stays locked until it finishes"), (r"SET NOT NULL", "reads every row while the table is locked"),
                (r"^\s*CREATE (UNIQUE )?INDEX (?!CONCURRENTLY)", "blocks writes to the table while the index builds"), (r"\bDROP (TABLE|COLUMN)\b", "removes data"), (r"GENERATED ALWAYS AS .* STORED", "computes the column for every row while the table is locked"))
SCHEMA_ROUTINE = (r"^\s*CREATE EXTENSION", r"^\s*CREATE OR REPLACE FUNCTION", r"^\s*DO \$\$", r"^\s*INSERT INTO users \(username, password, role\)", r"^\s*UPDATE users SET username = 'admin'")    # run on every start, whether anything changed or not

async def func_postgres_schema_plan(*, app_state: State, client_postgres: asyncpg.Pool, config_postgres_schema: dict, database: str = "master") -> list:
    """The statements startup would run to match config_postgres_schema, without running them: [{"sql", "risk", "table", "rows", "is_routine"}] (is_routine: runs on every start, whether anything changed or not). Catalog reads go to the database; every statement that would change it is recorded instead. Steps after a new table read the database as it is now, so a plan for a fresh database is incomplete."""
    class Recorder:
        def __init__(self, conn): self.conn, self.statements = conn, []
        async def fetch(self, *args, **kwargs): return await self.conn.fetch(*args, **kwargs)
        async def fetchrow(self, *args, **kwargs): return await self.conn.fetchrow(*args, **kwargs)
        async def fetchval(self, *args, **kwargs): return await self.conn.fetchval(*args, **kwargs)
        async def execute(self, sql, *args, **kwargs): self.statements.append(sql)
        def transaction(self): return contextlib.nullcontext()
    app_state.func_postgres_schema_config_validate(config_postgres_schema=config_postgres_schema)
    context = {**app_state.func_postgres_schema_context_build(config_postgres_schema=config_postgres_schema, users_setting=func_postgres_schema_users_setting(app_state=app_state)), "database": database}
    async with client_postgres.acquire() as conn:
        recorder = Recorder(conn)
        await func_postgres_schema_steps(app_state=app_state, conn=recorder, config_postgres_schema=config_postgres_schema, context=context, root_user_password_hash="(plan)", lock_timeout_sec=0)    # noqa: S106 - a placeholder: the hash is a bound value, never part of the recorded SQL
        rows = {r["relname"]: int(r["reltuples"]) for r in await conn.fetch("SELECT c.relname, c.reltuples FROM pg_class c JOIN pg_namespace n ON c.relnamespace = n.oid WHERE n.nspname = 'public' AND c.relkind = 'r'")}
    plan = []
    for sql in recorder.statements:
        risk = next((reason for pattern, reason in SCHEMA_RISKS if re.search(pattern, sql, re.IGNORECASE)), None)
        table = (re.search(r'(?:ALTER TABLE|ON|INTO|UPDATE)\s+(?:ONLY\s+)?"?(\w+)"?', sql, re.IGNORECASE) or [None, None])[1]
        plan.append({"sql": sql, "risk": risk, "table": table, "rows": max(rows.get(table, 0), 0) if table else None, "is_routine": any(re.search(pattern, sql) for pattern in SCHEMA_ROUTINE) or sql in func_postgres_schema_sql_queries(config_postgres_schema.get("sql", {}))})
    return plan
