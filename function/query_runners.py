"""Atom query runners functions."""

def func_clickhouse_query_runner_read_sql(*, sql: str, limit: int) -> str:
    """Validate a ClickHouse read query and wrap it with a server-side row limit."""
    sql = str(sql or "").strip().rstrip(";").strip()
    if not sql: raise Exception("SQL is required")
    if ";" in sql: raise Exception("Only one SQL statement is allowed")
    if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("Only SELECT/WITH queries are supported")
    return f"SELECT * FROM ({sql}) AS clickhouse_query LIMIT {int(limit)}"

async def func_clickhouse_query_runner_read(*, client_clickhouse: any, config_query_runner_read_limit: int, sql: str) -> list:
    """Run a read-only ClickHouse query and return row mappings up to the configured limit."""
    if not client_clickhouse: raise Exception("clickhouse client not initialized")
    sql = func_clickhouse_query_runner_read_sql(sql=sql, limit=config_query_runner_read_limit)
    result = await client_clickhouse.query(sql, settings={"readonly": 1, "max_execution_time": 30})
    return [dict(zip(result.column_names, row)) for row in result.result_rows]

async def func_clickhouse_query_runner_read_export(*, client_clickhouse: any, config_query_runner_export_limit: int, sql: str) -> any:
    """Stream a read-only ClickHouse query as CSV up to the configured export limit."""
    if not client_clickhouse: raise Exception("clickhouse client not initialized")
    sql = func_clickhouse_query_runner_read_sql(sql=sql, limit=config_query_runner_export_limit)
    async def _iter():
        stream = await client_clickhouse.raw_stream(sql, fmt="CSVWithNames", settings={"readonly": 1, "max_execution_time": 30})
        async with stream:
            async for chunk in stream:
                yield chunk
    return _iter()

async def func_clickhouse_query_runner_write(*, client_clickhouse: any, sql: str) -> str:
    """Run one non-read ClickHouse statement and return its command result."""
    if not client_clickhouse: raise Exception("clickhouse client not initialized")
    sql = str(sql or "").strip().rstrip(";").strip()
    if not sql: raise Exception("SQL is required")
    if ";" in sql: raise Exception("Only one SQL statement is allowed")
    ql = sql.lower().lstrip("(").strip()
    if ql.startswith(("select", "with", "explain", "show", "describe", "desc", "exists")): raise Exception("read SQL must use /admin/clickhouse-query-runner-read")
    result = await client_clickhouse.command(sql, settings={"max_execution_time": 30})
    return str(result)

def _mssql_read_sql(sql):
    """Reject write/batch commands before sending SQL to a read runner.

    This is defense in depth; the database login must also have read-only grants.
    """
    import re
    sql = str(sql or "").strip().rstrip(";").strip()
    if not sql or ";" in sql:
        raise Exception("Only one read SQL statement is allowed")
    if not re.match(r"^\(*\s*(select|with)\b", sql, re.IGNORECASE):
        raise Exception("read mode restricted")
    if re.search(r"\b(insert|update|delete|merge|drop|alter|create|truncate|exec|execute|into|grant|revoke|deny|backup|restore|dbcc|set|use|waitfor|shutdown|kill|reconfigure|openrowset|opendatasource|openquery)\b", sql, re.IGNORECASE):
        raise Exception("read mode restricted")
    return sql

async def func_mssql_query_runner_read_export(*, client_mssql: any, config_query_runner_export_limit: int, sql: str) -> any:
    """Runs a read-only MSSQL query and yields CSV lines up to the configured export limit."""
    import re
    import asyncio
    if not client_mssql: raise Exception("MSSQL client not initialized")
    sql = _mssql_read_sql(sql)
    limit = config_query_runner_export_limit
    async def _iter():
        for attempt in range(3):
            try:
                async with client_mssql.acquire() as conn:
                    cursor = await conn.cursor()
                    await cursor.execute(sql)
                    columns = [column[0] for column in cursor.description]
                    yield ",".join(columns) + "\n"
                    count = 0
                    while True:
                        rows = await cursor.fetchmany(min(500, limit - count))
                        if not rows: break
                        for row in rows:
                            yield ",".join([f"\"{str(v).replace(chr(34), chr(34)*2)}\"" if v is not None else "" for v in row]) + "\n"
                        count += len(rows)
                        if count >= limit: break
                    return
            except Exception as e:
                if "08S01" in str(e) and attempt < 2:
                    await asyncio.sleep(0.5)
                    continue
                raise e
    return _iter()

async def func_mssql_query_runner_read(*, client_mssql: any, config_query_runner_read_limit: int, sql: str) -> list:
    """Runs a read-only MSSQL query and returns matching records up to the configured limit."""
    import re
    import asyncio
    if not client_mssql: raise Exception("MSSQL client not initialized")
    sql = _mssql_read_sql(sql)
    limit = config_query_runner_read_limit
    for attempt in range(3):
        try:
            async with client_mssql.acquire() as conn:
                cursor = await conn.cursor()
                await cursor.execute(sql)
                columns = [column[0] for column in cursor.description]
                result = []
                while len(result) < limit:
                    rows = await cursor.fetchmany(min(500, limit - len(result)))
                    if not rows: break
                    result.extend(dict(zip(columns, row)) for row in rows)
                return result
        except Exception as e:
            if "08S01" in str(e) and attempt < 2:
                await asyncio.sleep(0.5)
                continue
            raise e

async def func_mssql_query_runner_write(*, client_mssql: any, sql: str) -> str:
    """Runs a write SQL query against the MSSQL instance and commits the transaction."""
    import asyncio
    if not client_mssql: raise Exception("MSSQL client not initialized")
    ql = sql.lower().strip().lstrip("(").strip()
    if ql.startswith(("select", "with")): raise Exception("read SQL must use /admin/mssql-query-runner-read")
    for attempt in range(3):
        try:
            async with client_mssql.acquire() as conn:
                cursor = await conn.cursor()
                await cursor.execute(sql)
                await conn.commit()
                return "done"
        except Exception as e:
            if "08S01" in str(e) and attempt < 2:
                await asyncio.sleep(0.5)
                continue
            raise e

async def func_postgres_query_runner_read(*, client_postgres: any, config_query_runner_read_limit: int, sql: str) -> list:
    """Runs a read-only PostgreSQL SELECT/WITH query and returns row mappings up to the configured limit."""
    sql = str(sql or "").strip().rstrip(";").strip()
    if not sql: raise Exception("SQL is required")
    if ";" in sql: raise Exception("Only one SQL statement is allowed")
    if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("Only SELECT/WITH queries are supported")
    if not client_postgres: raise Exception("postgres client not initialized")
    timeout_sec = 30
    async with client_postgres.acquire() as conn:
        async with conn.transaction(readonly=True):
            await conn.execute(f"SET LOCAL statement_timeout = '{timeout_sec * 1000}ms'")
            stmt = await conn.prepare(f"SELECT * FROM ({sql}) AS postgres_query LIMIT $1")
            records = await stmt.fetch(config_query_runner_read_limit, timeout=timeout_sec)
    return [dict(row) for row in records]

async def func_postgres_query_runner_read_export(*, client_postgres: any, config_query_runner_export_limit: int, sql: str) -> any:
    """Runs a read-only PostgreSQL SELECT/WITH query and yields CSV chunks up to the configured export limit."""
    import io
    import csv
    sql = str(sql or "").strip().rstrip(";").strip()
    if not sql: raise Exception("SQL is required")
    if ";" in sql: raise Exception("Only one SQL statement is allowed")
    if not sql.lower().lstrip("(").strip().startswith(("select", "with")): raise Exception("Only SELECT/WITH queries are supported")
    if not client_postgres: raise Exception("postgres client not initialized")
    timeout_sec = 30
    async def _iter():
        async with client_postgres.acquire() as conn:
            async with conn.transaction(readonly=True):
                await conn.execute(f"SET LOCAL statement_timeout = '{timeout_sec * 1000}ms'")
                stmt = await conn.prepare(f"SELECT * FROM ({sql}) AS postgres_query LIMIT $1")
                columns = [attr.name for attr in stmt.get_attributes()]
                buffer = io.StringIO()
                writer = csv.writer(buffer)
                writer.writerow(columns)
                yield buffer.getvalue()
                buffer.seek(0); buffer.truncate(0)
                async for record in stmt.cursor(config_query_runner_export_limit, prefetch=250, timeout=timeout_sec):
                    writer.writerow([record[column] for column in columns])
                    yield buffer.getvalue()
                    buffer.seek(0); buffer.truncate(0)
    return _iter()

async def func_postgres_query_runner_write(*, client_postgres: any, sql: str) -> str:
    """Runs a write SQL query against the PostgreSQL instance and returns the result command tag."""
    if not client_postgres: raise Exception("postgres client not initialized")
    ql = sql.lower().strip().lstrip("(").strip()
    if ql.startswith(("select", "with", "explain", "show", "describe")): raise Exception("read SQL must use /admin/postgres-query-runner-read")
    if "returning" in ql: raise Exception("RETURNING is not allowed in write mode")
    async with client_postgres.acquire() as conn:
        result = await conn.execute(sql, timeout=15)
    return result
