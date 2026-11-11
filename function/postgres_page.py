# import
import json
from typing import Any
from .middleware import func_api_error

# function
def func_page_keys(*, order: str, columns: dict, default: str = "id desc", alias: str = "") -> list:
    """The page keys of a list: order ("col [asc|desc] [nulls first|last], ...", checked against columns {name: {"datatype", "is_nullable"}}) as
    [{"name", "sql", "desc", "nulls", "type", "nullable"}], with id added last (in the direction of the last key) when the order omits it,
    so every row has one place in the order. Each column keeps its own direction; NULLs go where the order says, else last ascending and first descending (Postgres's default)."""
    keys = []
    for part in str(order or "").strip().split(",") if str(order or "").strip() else default.split(","):
        words = [word.lower() for word in part.split()]
        direction, nulls = (words[1:2] or ["asc"])[0], None
        if len(words) == 4 and words[2] == "nulls": nulls = words[3]
        elif len(words) == 3 and words[1] == "nulls": direction, nulls = "asc", words[2]
        if not words or len(words) > 4 or direction not in ("asc", "desc") or nulls not in (None, "first", "last") or (len(words) == 3 and nulls is None) or (len(words) == 4 and nulls is None): raise func_api_error(message=f"invalid order: {part.strip()}", status_code=400)
        name = part.split()[0]
        if name not in columns: raise func_api_error(message=f"order column '{name}' not found", status_code=400)
        if any(key["name"] == name for key in keys): raise func_api_error(message=f"order column '{name}' given twice", status_code=400)
        datatype = str(columns[name].get("datatype") or "text")
        if datatype.endswith("[]") or datatype.lower() in ("json", "jsonb", "bytea", "array"): raise func_api_error(message=f"cannot order by '{name}' ({datatype})", status_code=400)
        keys.append({"name": name, "sql": f'{alias}"{name}"', "desc": direction == "desc", "nulls": nulls or ("first" if direction == "desc" else "last"), "type": datatype, "nullable": columns[name].get("is_nullable") != "NO"})
    if "id" in columns and not any(key["name"] == "id" for key in keys):
        keys.append({"name": "id", "sql": f'{alias}"id"', "desc": keys[-1]["desc"], "nulls": "first" if keys[-1]["desc"] else "last", "type": str(columns["id"].get("datatype") or "bigint"), "nullable": False})
    return keys

def func_page_order_sql(*, keys: list) -> str:
    """The ORDER BY of a list (without the words ORDER BY), from func_page_keys; NULLS FIRST/LAST only where it differs from Postgres's default, so plain orders match plain indexes."""
    def nulls(key):
        default = "first" if key["desc"] else "last"
        return "" if key.get("nulls", default) == default else f' NULLS {key["nulls"].upper()}'
    return ", ".join(f'{key["sql"]} {"DESC" if key["desc"] else "ASC"}{nulls(key)}' for key in keys)

def func_page_after_where(*, keys: list, after: Any, values: list) -> str:
    """The condition for the rows after the cursor (after: the previous response's after), or "" for the first page; values are bound, never formatted into SQL.
    Written so an index on the keys jumps straight to the cursor: key1 <= v1 AND (key1 < v1 OR (key2 <= v2 AND (...))) for descending keys, the mirror for ascending,
    each key in its own direction, NULLs where the order puts them."""
    if after in (None, ""): return ""
    try:
        cursor = json.loads(after) if isinstance(after, str) else after
        if not isinstance(cursor, list) or len(cursor) != len(keys) or not all(value is None or (isinstance(value, (str, int, float)) and not isinstance(value, bool)) for value in cursor): raise ValueError
    except ValueError: raise func_api_error(message="after does not belong to this list: start from the first page", status_code=400) from None
    def condition(index):
        key, value = keys[index], cursor[index]
        column = key["sql"]
        nulls_last = key.get("nulls", "first" if key["desc"] else "last") == "last"
        if value is None:    # the cursor is in the NULLs: after them come the values (NULLs first) or nothing (NULLs last)
            strict, bound = ("FALSE", f"{column} IS NULL") if nulls_last else (f"{column} IS NOT NULL", "")
        else:
            values.append(str(value))
            mark, sign = f"${len(values)}::text::{key['type']}", "<" if key["desc"] else ">"
            strict, bound = f"{column} {sign} {mark}", f"{column} {sign}= {mark}"
            if key["nullable"] and nulls_last: strict, bound = f"({strict} OR {column} IS NULL)", f"({bound} OR {column} IS NULL)"    # NULLs still to come
        if index == len(keys) - 1: return strict
        rest = f"({strict} OR {condition(index + 1)})"
        return f"({bound} AND {rest})" if bound else rest
    return condition(0)

def func_page_offset(*, page: Any, after: Any, limit: int, offset_max: int) -> int:
    """The OFFSET of an optional page number: 0 without page. page jumps to page N within the first offset_max rows (config_page_offset_max),
    worked out from the params alone, never by counting the table; deeper, or page with after, is a 400. after stays the way to page on."""
    if page is None: return 0
    if after not in (None, ""): raise func_api_error(message="send page or after, not both", status_code=400)
    if not isinstance(page, int) or isinstance(page, bool) or page < 1: raise func_api_error(message="page must be 1 or more", status_code=400)
    offset = (page - 1) * limit
    if offset_max and offset > offset_max: raise func_api_error(message=f"page reaches past {offset_max:,} rows: page on with after", status_code=400)
    return offset

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
