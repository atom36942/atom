# import
import csv
import io
from datetime import date
from datetime import datetime
from typing import Any
import asyncpg
import orjson
from argon2 import PasswordHasher
from .postgres_crud import func_postgres_read

# function
def func_csv_cell(value: Any) -> Any:
    """Format one value for CSV: JSON for dicts and lists, ISO dates, and a leading ' on text that spreadsheets would run as a formula."""
    if value is None: return ""
    if isinstance(value, (dict, list, tuple)): value = orjson.dumps(value, default=str).decode()
    elif isinstance(value, (date, datetime)): return value.isoformat()
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"): return "'" + value
    return value

async def func_postgres_read_export(*, client_postgres: asyncpg.Pool | None, client_password_hasher: PasswordHasher | None, cache_postgres_schema: dict, config_sql_read_limit_max: int, table: str, filter: list, order: str, column: str, export_limit: int, config_column_read_blocked: list = None, blocked_tables: list = None, batch_size: int = 1000) -> Any:
    """Read rows through func_postgres_read in batches and return a CSV generator, so every read rule (blocked tables and columns, filters) applies.

    The first batch is read before returning, so invalid input raises a normal API error instead of breaking a started download.
    """
    batch_size = max(1, min(batch_size, config_sql_read_limit_max, export_limit))
    async def read(page, after_id=None):
        rows = await func_postgres_read(client_postgres=client_postgres, client_password_hasher=client_password_hasher, cache_postgres_schema=cache_postgres_schema, config_sql_read_limit_max=config_sql_read_limit_max, config_sql_read_relation_fetch_limit_max=0, table=table, filter=filter, limit=batch_size, page=page, order=order, column=column, relation=[], config_column_read_blocked=config_column_read_blocked, blocked_tables=blocked_tables, after_id=after_id)
        return rows[:batch_size], len(rows) > batch_size
    first_rows, has_more = await read(1)
    # sorted by id alone with id in the rows: each next batch starts after the last id (an index range), not at an ever larger OFFSET that Postgres reads and discards
    order_parts = (str(order or "").strip() or "id desc").lower().split()
    is_keyset = "," not in str(order or "") and order_parts[0] == "id" and order_parts[1:] in ([], ["asc"], ["desc"]) and bool(first_rows) and "id" in first_rows[0]
    if first_rows: columns = list(first_rows[0].keys())
    elif column.strip() != "*": columns = [c.strip() for c in column.split(",") if c.strip()]
    else: columns = [c for c in cache_postgres_schema.get(table, {}) if c not in set(config_column_read_blocked or ["password"])]
    async def _iter():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(columns)
        rows, more, page, sent = first_rows, has_more, 1, 0
        while True:
            rows = rows[:export_limit - sent]
            for row in rows: writer.writerow([func_csv_cell(row.get(c)) for c in columns])
            sent += len(rows)
            yield buffer.getvalue()
            buffer.seek(0); buffer.truncate(0)
            if not more or sent >= export_limit: break
            page += 1
            rows, more = await (read(1, after_id=rows[-1]["id"]) if is_keyset and rows else read(page))
    return _iter()
