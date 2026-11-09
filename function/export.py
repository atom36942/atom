# import
import asyncio
import csv
import io
from collections.abc import AsyncIterator
from collections.abc import Callable
from datetime import date
from datetime import datetime
from typing import Any
import asyncpg
import orjson
from argon2 import PasswordHasher
from fastapi.responses import StreamingResponse
from .clients import func_postgres_acquire_clean
from .middleware import func_api_error
from .postgres_crud import func_postgres_read_sql
from .query_runners import _clickhouse_read_settings
from .query_runners import _mssql_read_sql
from .query_runners import func_clickhouse_query_runner_read_sql

# function
def func_csv_cell(value: Any) -> Any:
    """Format one value for CSV: JSON for dicts and lists, ISO dates, and a leading ' on text that spreadsheets would run as a formula."""
    if value is None: return ""
    if isinstance(value, (dict, list, tuple)): value = orjson.dumps(value, default=str).decode()
    elif isinstance(value, (date, datetime)): return value.isoformat()
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"): return "'" + value
    return value

async def func_csv_stream(*, rows: AsyncIterator, columns: list, row: Callable | None = None) -> AsyncIterator[str]:
    """CSV text from any database's rows: a UTF-8 BOM (so Excel reads accents), the header, then every row's cells through func_csv_cell, sent in 64 KB chunks so memory stays flat at any size. row(record) -> list of values renames or relabels a row; without it the record's values go out as they are."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    yield "﻿" + buffer.getvalue()
    buffer.seek(0); buffer.truncate(0)
    async for record in rows:
        writer.writerow([func_csv_cell(value) for value in (row(record) if row else record)])
        if buffer.tell() >= 65536:
            yield buffer.getvalue()
            buffer.seek(0); buffer.truncate(0)
    if buffer.tell(): yield buffer.getvalue()

async def _csv_started(chunks: AsyncIterator[str]) -> AsyncIterator[str]:
    """Run an export up to its header before the response starts, so a bad query or a missing connection is a normal API error, not a broken download."""
    first = await chunks.__anext__()
    async def stream():
        try:
            yield first
            async for chunk in chunks: yield chunk
        finally: await chunks.aclose()
    return stream()

def func_export_limit(*, config_export_limit: int, limit: int | None = None) -> int:
    """The rows an export may send: the caller's limit (a user's choice), never more than config_export_limit; a bigger one is a 400 that names the maximum."""
    if limit is None: return config_export_limit
    if not 1 <= int(limit) <= config_export_limit: raise func_api_error(message=f"Rows must be between 1 and {config_export_limit:,}.", status_code=400)
    return int(limit)

def func_csv_response(*, content: AsyncIterator[str], filename: str) -> StreamingResponse:
    """The download response for a func_*_export stream."""
    return StreamingResponse(content, media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})

async def func_postgres_export(*, client_postgres: asyncpg.Pool | None, config_export_limit: int, sql: str, limit: int | None = None, values: list | tuple = (), columns: list | None = None, row: Callable | None = None, timeout_sec: int = 60) -> AsyncIterator[str]:
    """Every PostgreSQL CSV export (Atom's and a project's): one SELECT/WITH (values bound as $1, $2), at most limit rows (a user's choice, default and maximum config_export_limit), read with a cursor in a read-only transaction (timeout_sec per fetch) and streamed through func_csv_stream; no count, no OFFSET. columns: header names (default the query's); row: see func_csv_stream."""
    if not client_postgres: raise func_api_error(message="postgres client not initialized", status_code=500)
    limit = func_export_limit(config_export_limit=config_export_limit, limit=limit)
    sql = str(sql or "").strip().rstrip(";").strip()
    if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("Only SELECT/WITH queries are supported")
    async def chunks():
        async with func_postgres_acquire_clean(client_postgres=client_postgres) as conn:
            async with conn.transaction(readonly=True):
                await conn.execute(f"SET LOCAL statement_timeout = '{int(timeout_sec) * 1000}ms'")
                statement = await conn.prepare(f"SELECT * FROM ({sql}) AS export_query LIMIT ${len(values) + 1}")  # noqa: S608 - one read-only statement; the caller's values are bound
                async def records():
                    async for record in statement.cursor(*values, limit, prefetch=5000, timeout=timeout_sec): yield record if row else record.values()
                async for chunk in func_csv_stream(rows=records(), columns=columns or [attribute.name for attribute in statement.get_attributes()], row=row): yield chunk
    return await _csv_started(chunks())

async def func_postgres_read_export(*, client_postgres: asyncpg.Pool | None, client_password_hasher: PasswordHasher | None, cache_postgres_schema: dict, config_export_limit: int, table: str, filter: list, order: str, column: str, config_column_read_blocked: list = None, limit: int | None = None) -> AsyncIterator[str]:
    """A table as CSV through func_postgres_export, with every read rule of func_postgres_read (blocked columns, filters, order); "*" means every column a reader may see."""
    blocked = set(config_column_read_blocked) if config_column_read_blocked is not None else {"password"}
    if str(column).strip() == "*": column = ",".join(c for c in (cache_postgres_schema or {}).get(table, {}) if c not in blocked) or "*"
    sql, values = await func_postgres_read_sql(client_postgres=client_postgres, client_password_hasher=client_password_hasher, cache_postgres_schema=cache_postgres_schema, table=table, filter=filter, order=order, column=column, config_column_read_blocked=config_column_read_blocked)
    return await func_postgres_export(client_postgres=client_postgres, config_export_limit=config_export_limit, sql=sql, values=values, limit=limit)

async def func_mssql_export(*, client_mssql: Any, config_export_limit: int, sql: str, limit: int | None = None, columns: list | None = None, row: Callable | None = None) -> AsyncIterator[str]:
    """Every MSSQL CSV export: one read-only SELECT/WITH, at most config_export_limit rows, fetched in batches and streamed through func_csv_stream; a dropped connection (08S01) is retried until the first row goes out."""
    if not client_mssql: raise func_api_error(message="MSSQL client not initialized", status_code=500)
    limit = func_export_limit(config_export_limit=config_export_limit, limit=limit)
    sql = _mssql_read_sql(sql)
    async def chunks():
        for attempt in range(3):
            sent = False
            try:
                async with client_mssql.acquire() as conn:
                    cursor = await conn.cursor()
                    await cursor.execute(sql)
                    async def records(cursor=cursor):
                        count = 0
                        while count < limit:
                            batch = await cursor.fetchmany(min(5000, limit - count))
                            if not batch: return
                            count += len(batch)
                            for record in batch: yield record
                    async for chunk in func_csv_stream(rows=records(), columns=columns or [column[0] for column in cursor.description], row=row):
                        sent = True
                        yield chunk
                return
            except Exception as e:
                if not sent and "08S01" in str(e) and attempt < 2:
                    await asyncio.sleep(0.5)
                    continue
                raise
    return await _csv_started(chunks())

async def func_clickhouse_export(*, client_clickhouse: Any, config_export_limit: int, sql: str, limit: int | None = None, columns: list | None = None, row: Callable | None = None) -> AsyncIterator[str]:
    """Every ClickHouse CSV export: one read-only SELECT/WITH, at most config_export_limit rows (a server-side LIMIT), read as row blocks and streamed through func_csv_stream."""
    if not client_clickhouse: raise func_api_error(message="clickhouse client not initialized", status_code=500)
    sql = func_clickhouse_query_runner_read_sql(sql=sql, limit=func_export_limit(config_export_limit=config_export_limit, limit=limit))
    async def chunks():
        stream = await client_clickhouse.query_row_block_stream(sql, settings=_clickhouse_read_settings(client_clickhouse))
        async with stream:
            async def records():
                async for block in stream:
                    for record in block: yield record
            async for chunk in func_csv_stream(rows=records(), columns=columns or list(stream.source.column_names), row=row): yield chunk
    return await _csv_started(chunks())
