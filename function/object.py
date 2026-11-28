# import
import asyncpg
from starlette.datastructures import State
from .middleware import func_api_error
from .validation import func_postgres_rule_database

# function
AUDIT_COLUMNS = {    # never sent by a request: Atom or the database fills them, in every table that has them
"created_at": "database: default now(), on create",
"created_by_id": "Atom: the token's user, on create (also always a row's owner for /my)",
"updated_at": "database: trigger (control.is_updated_at_set), on update",
"updated_by_id": "Atom: the token's user, on update",
"deleted_at": "database clock: now(), on soft delete (mode=soft)",
"deleted_by_id": "Atom: the token's user, on soft delete (mode=soft)",
}
OBJECT_ACTIONS = {"read": "read", "create": "write", "update": "write", "delete": "delete", "delete_all": "delete"}    # action -> what the gate checks besides table access

def func_object_rule(*, app_state: State, table: str, connection: str = None) -> dict:
    """One table's rules from config_postgres_schema_<connection> (cache_postgres_table_rule; a connection without its own schema follows master's): access lists, read_blocked, write_blocked, ownership; {} when the table is in no schema."""
    return ((getattr(app_state, "cache_postgres_table_rule", None) or {}).get(func_postgres_rule_database(app_state=app_state, connection=connection)) or {}).get(table) or {}

def func_object_access(*, app_state: State, connection: str = None, table: str, group: str, action: str, relation: list = None, ownership_column: str = None, obj_list: list = None) -> list:
    """The one gate of Atom's table routes (/public, /private, /my, /admin object and table-column routes, CSV import); a project route uses it only if it calls it.
    group: the route's prefix (my, public, private, admin). action: read, create, update, delete, delete_all.
    Checks, in order: the table (and every table a read joins) is open to the group (control access lists; admin: any table of the schema), 403;
    for /my, ownership_column is created_by_id or a column of the table whose ownership lists the action, 403;
    for create / update, no row sends an audit column (AUDIT_COLUMNS) or a column whose write_blocked lists the group, 400.
    Returns the columns the group may not read for read (the read_blocked of the table, and of every joined table, for the group); [] otherwise."""
    if action not in OBJECT_ACTIONS: raise ValueError(f"func_object_access: action {action!r}; one of {', '.join(OBJECT_ACTIONS)}")
    app_state.func_check_table_access(app_state=app_state, connection=connection, table=table, group=group, action=action, relation=relation)
    rule = func_object_rule(app_state=app_state, table=table, connection=connection)
    if group == "my" and ownership_column is not None:
        if action == "create": raise ValueError("func_object_access: a create has no ownership_column (Atom sets created_by_id)")
        owners = (rule.get("ownership") or {}).get({"read": "read", "update": "update", "delete": "delete", "delete_all": "delete"}[action]) or []
        if ownership_column not in owners: raise func_api_error(message=f"ownership_column {ownership_column} not allowed for my {action} on {table}: created_by_id, or a column whose ownership lists {action if action != 'delete_all' else 'delete'}" + (f" ({', '.join(owners)})" if owners else ""), status_code=403)
    if OBJECT_ACTIONS[action] == "write":
        blocked = set(AUDIT_COLUMNS) | set((rule.get("write_blocked") or {}).get(group) or [])
        if columns := sorted({column for obj in obj_list or [] if isinstance(obj, dict) for column in obj if column in blocked}): raise func_api_error(message=f"{', '.join(columns)}: not writable by {group} ({'set by Atom' if set(columns) <= set(AUDIT_COLUMNS) else 'write_blocked'})", status_code=400)
    if OBJECT_ACTIONS[action] == "read":    # the table's read_blocked for the group, plus that of every table the read joins (relation "key,table,..."), so a joined users row never shows its password
        joined = [parts[1] for rel in relation or [] if len(parts := [p.strip() for p in str(rel).split(",", 4)]) >= 2]
        blocked = []
        for name in [table, *joined]:
            blocked += [column for column in ((func_object_rule(app_state=app_state, table=name, connection=connection).get("read_blocked") or {}).get(group) or []) if column not in blocked]
        return blocked
    return []

def func_object_write_blocked(*, app_state: State, table: str, group: str, connection: str = None) -> list:
    """The columns a group may not write in a table: AUDIT_COLUMNS plus the columns whose write_blocked lists the group (the user routes use it for users)."""
    return [*AUDIT_COLUMNS, *[column for column in (func_object_rule(app_state=app_state, table=table, connection=connection).get("write_blocked") or {}).get(group) or [] if column not in AUDIT_COLUMNS]]

def func_object_read_blocked(*, app_state: State, table: str, group: str, connection: str = None) -> list:
    """The columns a group may not read in a table: the columns whose read_blocked lists the group."""
    return list((func_object_rule(app_state=app_state, table=table, connection=connection).get("read_blocked") or {}).get(group) or [])

async def func_object_soft_delete(*, client_postgres: asyncpg.Pool, cache_postgres_schema: dict, table: str, ids: list, user_id: int, mode: str = "soft", ownership_column: str = None, owner_id: int = None) -> int:
    """Soft delete (mode soft) or restore (mode restore) rows by id: deleted_at = now() and deleted_by_id = user_id (when the table has it), or deleted_at = NULL; updated_by_id = user_id when the table has it.
    ownership_column / owner_id limit it to one user's rows (/my). Only rows not yet deleted are deleted, and only deleted ones restored. Returns how many rows changed."""
    columns = (cache_postgres_schema or {}).get(table) or {}
    if "deleted_at" not in columns: raise func_api_error(message=f"table {table} has no deleted_at column: soft delete needs one", status_code=400)
    if mode not in ("soft", "restore"): raise ValueError(f"func_object_soft_delete: mode {mode!r}; soft or restore")
    values, sets = [list(ids), user_id], ["\"deleted_at\" = now()" if mode == "soft" else "\"deleted_at\" = NULL"]
    if mode == "soft" and "deleted_by_id" in columns: sets.append("\"deleted_by_id\" = $2")
    if mode == "restore" and "deleted_by_id" in columns: sets.append("\"deleted_by_id\" = NULL")
    if "updated_by_id" in columns: sets.append("\"updated_by_id\" = $2")
    where = ["\"id\" = ANY($1::bigint[])", "\"deleted_at\" IS NULL" if mode == "soft" else "\"deleted_at\" IS NOT NULL"]
    if ownership_column:
        values.append(owner_id)
        where.append(f"\"{ownership_column}\" = $3")
    if ownership_column and ownership_column not in columns: raise func_api_error(message=f"table {table} has no column {ownership_column}", status_code=400)
    sql = f"UPDATE \"{table}\" SET {', '.join(sets)} WHERE {' AND '.join(where)}"  # noqa: S608 - table and ownership_column are columns of the cached schema, values are bound
    if "$2" not in sql: sql, values = sql.replace("$3", "$2"), [values[0], *values[2:]]
    result = await client_postgres.execute(sql, *values)
    return int(result.split()[-1]) if isinstance(result, str) and result.split()[-1].isdigit() else 0
