# import
import re
from typing import Any
import asyncpg
from starlette.datastructures import State
from .middleware import func_api_error
from .postgres_page import func_page_after_next
from .postgres_page import func_page_after_where
from .postgres_page import func_page_keys
from .postgres_page import func_page_offset
from .postgres_page import func_page_order_sql

# function
async def func_postgres_table_column_groupby_read(*, app_state: State, client_postgres: asyncpg.Pool | None, cache_postgres_schema: dict, table: str, col: Any, limit: int, after: Any = None, page: int | None = None, agg: str = "count", agg_col: str = "*", order: str = "count desc", filter: list = None) -> dict:
    """Rows per value of one or more columns with an aggregate (count, sum, avg, min, max): {"obj_list", "after"}, one page after the cursor (func_page_keys over the result columns, the group columns as tie-breakers), never OFFSET."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    if limit < 1: raise Exception("query limit must be greater than 0")
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
    agg_type = {"count": "bigint", "sum": "numeric", "avg": "numeric"}.get(agg) or cache_postgres_schema[table].get(agg_col, {}).get("datatype", "numeric")
    columns = {c: {"datatype": str(cache_postgres_schema[table][c].get("datatype", "text")).removesuffix("[]"), "is_nullable": "YES"} for c in cols}
    columns[agg_field] = {"datatype": agg_type, "is_nullable": "YES"}
    words = (order or "count desc").strip().lower().split()
    direction = "desc" if "desc" in words else "asc"
    if words and words[0] in ("count", agg, agg_field): first = agg_field
    elif words and words[0] == "item": first = cols[0]
    elif words and words[0] in cols: first = words[0]
    else: first, direction = agg_field, "desc"
    keys = func_page_keys(order=", ".join([f"{first} {direction}", *[f"{c} asc" for c in cols if c != first]]), columns=columns, alias="g.")
    select_sql = ", ".join(select_exprs)
    group_sql = ", ".join(group_exprs)
    source_sql = f' {" ".join(unnest_clauses)}' if unnest_clauses else ""
    offset = func_page_offset(page=page, after=after, limit=limit, offset_max=getattr(app_state, "config_page_offset_max", 10000))
    after_sql = func_page_after_where(keys=keys, after=after, values=values)
    values.append(limit + 1)
    sql = f'SELECT * FROM (SELECT {select_sql} FROM "{table}" x{source_sql} {where_clause} GROUP BY {group_sql}) g {"WHERE " + after_sql if after_sql else ""} ORDER BY {func_page_order_sql(keys=keys)} LIMIT ${len(values)}{f" OFFSET {offset}" if offset else ""}'  # noqa: S608 - identifiers pattern-checked and quoted, values bound as $n
    async with client_postgres.acquire() as conn:
        rows = await conn.fetch(sql, *values)
    return {"obj_list": [dict(row) for row in rows[:limit]], "after": func_page_after_next(keys=keys, rows=rows, limit=limit)}

async def func_postgres_table_column_distinct_read(*, app_state: State, client_postgres: asyncpg.Pool | None, cache_postgres_schema: dict, table: str, col: str, limit: int, after: Any = None, page: int | None = None, order: str = "item asc", filter: list = None) -> dict:
    """The distinct values of one column (each element of an array column): {"item_list", "after"}, one page after the cursor, never OFFSET."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    if limit < 1: raise Exception("query limit must be greater than 0")
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
    keys = func_page_keys(order=f'item {"desc" if "desc" in (order or "").lower() else "asc"}', columns={"item": {"datatype": datatype.removesuffix("[]"), "is_nullable": "YES"}}, alias="d.")
    source_sql = f'CROSS JOIN LATERAL unnest(x.{q_col}) item_col' if is_array else ""
    item_sql = "item_col" if is_array else f'x.{q_col}'
    offset = func_page_offset(page=page, after=after, limit=limit, offset_max=getattr(app_state, "config_page_offset_max", 10000))
    after_sql = func_page_after_where(keys=keys, after=after, values=values)
    values.append(limit + 1)
    sql = f'SELECT d.item FROM (SELECT DISTINCT {item_sql} AS item FROM "{table}" x {source_sql} {where_clause}) d {"WHERE " + after_sql if after_sql else ""} ORDER BY {func_page_order_sql(keys=keys)} LIMIT ${len(values)}{f" OFFSET {offset}" if offset else ""}'  # noqa: S608 - identifiers pattern-checked and quoted, values bound as $n
    async with client_postgres.acquire() as conn:
        rows = await conn.fetch(sql, *values)
    return {"item_list": [row["item"] for row in rows[:limit]], "after": func_page_after_next(keys=keys, rows=rows, limit=limit)}
