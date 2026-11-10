# import
import json
from typing import Any
from .middleware import func_api_error

# function
def func_page_keys(*, order: str, columns: dict, default: str = "id desc", alias: str = "") -> list:
    """The page keys of a list: order ("col asc, col desc", checked against columns {name: {"datatype", "is_nullable"}}) as
    [{"name", "sql", "desc", "type", "nullable"}], with id added last (in the direction of the last key) when the order omits it,
    so every row has one place in the order. Postgres sorts NULLs last when ascending and first when descending; the cursor follows that."""
    keys = []
    for part in str(order or "").strip().split(",") if str(order or "").strip() else default.split(","):
        words = part.split()
        if not words or len(words) > 2 or (len(words) == 2 and words[1].lower() not in ("asc", "desc")): raise func_api_error(message=f"invalid order: {part.strip()}", status_code=400)
        name = words[0]
        if name not in columns: raise func_api_error(message=f"order column '{name}' not found", status_code=400)
        if any(key["name"] == name for key in keys): raise func_api_error(message=f"order column '{name}' given twice", status_code=400)
        datatype = str(columns[name].get("datatype") or "text")
        if datatype.endswith("[]") or datatype.lower() in ("json", "jsonb", "bytea", "array"): raise func_api_error(message=f"cannot order by '{name}' ({datatype})", status_code=400)
        keys.append({"name": name, "sql": f'{alias}"{name}"', "desc": len(words) == 2 and words[1].lower() == "desc", "type": datatype, "nullable": columns[name].get("is_nullable") != "NO"})
    if "id" in columns and not any(key["name"] == "id" for key in keys):
        keys.append({"name": "id", "sql": f'{alias}"id"', "desc": keys[-1]["desc"], "type": str(columns["id"].get("datatype") or "bigint"), "nullable": False})
    return keys

def func_page_order_sql(*, keys: list) -> str:
    """The ORDER BY of a list (without the words ORDER BY), from func_page_keys."""
    return ", ".join(f'{key["sql"]} {"DESC" if key["desc"] else "ASC"}' for key in keys)

def func_page_after_where(*, keys: list, after: Any, values: list) -> str:
    """The condition for the rows after the cursor (after: the previous response's after), or "" for the first page; values are bound, never formatted into SQL.
    Written so an index on the keys jumps straight to the cursor: key1 <= v1 AND (key1 < v1 OR (key2 <= v2 AND (...))) for descending keys, the mirror for ascending."""
    if after in (None, ""): return ""
    try:
        cursor = json.loads(after) if isinstance(after, str) else after
        if not isinstance(cursor, list) or len(cursor) != len(keys) or not all(value is None or (isinstance(value, (str, int, float)) and not isinstance(value, bool)) for value in cursor): raise ValueError
    except ValueError: raise func_api_error(message="after does not belong to this list: start from the first page", status_code=400) from None
    def condition(index):
        key, value = keys[index], cursor[index]
        column = key["sql"]
        if value is None:
            strict, bound = (f"{column} IS NOT NULL", "") if key["desc"] else ("FALSE", f"{column} IS NULL")
        else:
            values.append(str(value))
            mark = f"${len(values)}::text::{key['type']}"
            if key["desc"]: strict, bound = f"{column} < {mark}", f"{column} <= {mark}"
            elif key["nullable"]: strict, bound = f"({column} > {mark} OR {column} IS NULL)", f"({column} >= {mark} OR {column} IS NULL)"
            else: strict, bound = f"{column} > {mark}", f"{column} >= {mark}"
        if index == len(keys) - 1: return strict
        rest = f"({strict} OR {condition(index + 1)})"
        return f"({bound} AND {rest})" if bound else rest
    return condition(0)

def func_page_after_next(*, keys: list, rows: list, limit: int) -> str | None:
    """The after of the next page: the key values of this page's last row, as JSON text, when the list read limit + 1 rows and got the extra one; None on the last page."""
    if len(rows) <= limit: return None
    last = rows[limit - 1]
    def text(value):
        if value is None: return None
        if isinstance(value, bool): return "true" if value else "false"
        if hasattr(value, "isoformat"): return value.isoformat()
        return str(value)
    return json.dumps([text(last[key["name"]]) for key in keys], separators=(",", ":"))
