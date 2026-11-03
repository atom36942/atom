# import
import re
from typing import Any
import asyncpg
from starlette.datastructures import State
from .middleware import func_api_error

# function
async def func_postgres_table_column_groupby_read(*, app_state: State, client_postgres: asyncpg.Pool | None, cache_postgres_schema: dict, table: str, col: Any, limit: int, page: int, agg: str = "count", agg_col: str = "*", order: str = "count desc", filter: list = None) -> dict:
    """Executes a PostgreSQL GROUP BY query dynamically across single or multiple columns and returns flat paginated results."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    if limit < 1: raise Exception("query limit must be greater than 0")
    if page < 1: raise Exception("page must be greater than 0")
    if app_state.config_sql_read_limit_max and limit > app_state.config_sql_read_limit_max: raise Exception(f"query limit {limit} exceeds maximum allowed: {app_state.config_sql_read_limit_max}")
    if table not in cache_postgres_schema: raise Exception(f"table '{table}' not found")
    cols = [col] if isinstance(col, str) else list(col or [])
    if not cols: raise Exception("at least one column must be specified")
    blocked_cols = set(getattr(app_state, "config_column_read_blocked", [])) | {"password"}
    for c in cols:
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(c)): raise Exception(f"invalid identifier: {c}")
        if c in blocked_cols: raise Exception(f"reading column '{c}' is blocked")
        if c not in cache_postgres_schema[table]: raise Exception(f"column '{c}' not found in table: {table}")
    agg = (agg or "count").lower()
    if agg not in ["count", "sum", "avg", "min", "max"]: raise Exception(f"unsupported agg: {agg}")
    if agg_col != "*":
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(agg_col)): raise Exception("invalid aggregate column")
        if agg_col in blocked_cols: raise Exception(f"reading column '{agg_col}' is blocked")
        if agg_col not in cache_postgres_schema[table]: raise Exception(f"column '{agg_col}' not found in table: {table}")
    where_clause, values = await app_state.func_postgres_where_build(client_postgres=client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=cache_postgres_schema, table=table, filter=filter or [], prefix="x.", config_column_read_blocked=getattr(app_state, "config_column_read_blocked", None))
    select_exprs, group_exprs, unnest_clauses = [], [], []
    for c in cols:
        dt = cache_postgres_schema.get(table, {}).get(c, {}).get("datatype", "text").lower()
        is_array = "[]" in dt or "array" in dt
        if is_array:
            alias_c = f"{c}_item"
            unnest_clauses.append(f'CROSS JOIN LATERAL unnest(x."{c}") "{alias_c}"')
            select_exprs.append(f'"{alias_c}" AS "{c}"')
            group_exprs.append(f'"{alias_c}"')
        else:
            select_exprs.append(f'x."{c}" AS "{c}"')
            group_exprs.append(f'x."{c}"')
    agg_field = "count" if agg == "count" and agg_col == "*" else (f"{agg}_{agg_col}" if agg_col != "*" else agg)
    agg_col_sql = f'x."{agg_col}"' if agg_col != "*" else "*"
    select_exprs.append(f'{agg.upper()}({agg_col_sql}) AS "{agg_field}"')
    order = (order or "count desc").strip()
    order_lower = order.lower()
    if "count" in order_lower or agg in order_lower:
        order_dir = "DESC" if "desc" in order_lower else "ASC"
        order_sql = f'"{agg_field}" {order_dir}'
    elif "item desc" in order_lower or "item asc" in order_lower:
        order_dir = "DESC" if "desc" in order_lower else "ASC"
        order_sql = f'{group_exprs[0]} {order_dir}'
    else:
        parts = order.split()
        order_col_name = parts[0]
        order_dir = parts[1].upper() if len(parts) > 1 and parts[1].lower() in ("asc", "desc") else "ASC"
        if order_col_name in cols:
            dt = cache_postgres_schema.get(table, {}).get(order_col_name, {}).get("datatype", "text").lower()
            order_sql = f'"{order_col_name}_item" {order_dir}' if ("[]" in dt or "array" in dt) else f'x."{order_col_name}" {order_dir}'
        else:
            order_sql = f'"{agg_field}" DESC'
    order_sql = f'{order_sql}, {", ".join(group_exprs)}'
    select_sql = ", ".join(select_exprs)
    group_sql = ", ".join(group_exprs)
    source_sql = f' {" ".join(unnest_clauses)}' if unnest_clauses else ""
    bind_idx = len(values) + 1
    sql = f'SELECT {select_sql} FROM "{table}" x{source_sql} {where_clause} GROUP BY {group_sql} ORDER BY {order_sql} LIMIT ${bind_idx} OFFSET ${bind_idx + 1}'  # noqa: S608 - identifiers pattern-checked and quoted, values bound as $n
    values.extend([limit + 1, (page - 1) * limit])
    async with client_postgres.acquire() as conn:
        rows = await conn.fetch(sql, *values)
    ol = [dict(row) for row in rows]
    return {"obj_list": ol[:limit], "has_next_page": len(ol) > limit}

async def func_postgres_table_column_distinct_read(*, app_state: State, client_postgres: asyncpg.Pool | None, cache_postgres_schema: dict, table: str, col: str, limit: int, page: int, order: str = "item asc", filter: list = None) -> dict:
    """Read paginated distinct values for a single column."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    if limit < 1: raise Exception("query limit must be greater than 0")
    if page < 1: raise Exception("page must be greater than 0")
    if app_state.config_sql_read_limit_max and limit > app_state.config_sql_read_limit_max: raise Exception(f"query limit {limit} exceeds maximum allowed: {app_state.config_sql_read_limit_max}")
    if table not in cache_postgres_schema: raise Exception(f"table '{table}' not found")
    blocked_cols = set(getattr(app_state, "config_column_read_blocked", [])) | {"password"}
    if col in blocked_cols: raise Exception(f"reading column '{col}' is blocked")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(col)): raise Exception(f"invalid identifier: {col}")
    if col not in cache_postgres_schema[table]: raise Exception(f"column '{col}' not found in table: {table}")
    where_clause, values = await app_state.func_postgres_where_build(client_postgres=client_postgres, client_password_hasher=app_state.client_password_hasher, cache_postgres_schema=cache_postgres_schema, table=table, filter=filter or [], prefix="x.", config_column_read_blocked=getattr(app_state, "config_column_read_blocked", None))
    datatype = cache_postgres_schema[table][col].get("datatype", "text").lower()
    is_array = "[]" in datatype or "array" in datatype
    q_col = f'"{col}"'
    order_direction = "DESC" if "desc" in (order or "").lower() else "ASC"
    bind_idx = len(values) + 1
    source_sql = f'CROSS JOIN LATERAL unnest(x.{q_col}) item_col' if is_array else ""
    item_sql = "item_col" if is_array else f'x.{q_col}'
    sql = f'SELECT DISTINCT {item_sql} AS item FROM "{table}" x {source_sql} {where_clause} ORDER BY item {order_direction} LIMIT ${bind_idx} OFFSET ${bind_idx + 1}'  # noqa: S608 - identifiers pattern-checked and quoted, values bound as $n
    values.extend([limit + 1, (page - 1) * limit])
    async with client_postgres.acquire() as conn:
        rows = await conn.fetch(sql, *values)
    items = [row["item"] for row in rows]
    return {"item_list": items[:limit], "has_next_page": len(items) > limit}
