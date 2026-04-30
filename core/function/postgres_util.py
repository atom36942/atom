async def func_table_tag_read(*, client_postgres_pool: any, table: str, column: str, limit: int, page: int, filter_column: str, filter_value: any) -> list:
    """Read unique tags/items from an array column with occurrence counts."""
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)):
        raise Exception(f"invalid identifier {table}")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(column)):
        raise Exception(f"invalid identifier {column}")
    if filter_column and not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(filter_column)):
        raise Exception(f"invalid identifier {filter_column}")
    where_clause = ""
    query_args = []
    if filter_column and filter_value is not None:
        where_clause = f"WHERE x.{filter_column}=$1"
        query_args = [filter_value]
    query = f"SELECT tag_item, count(*) FROM {table} x CROSS JOIN LATERAL unnest(x.{column}) tag_item {where_clause} GROUP BY tag_item ORDER BY count(*) DESC LIMIT {limit} OFFSET {(page-1)*limit}"
    async with client_postgres_pool.acquire() as conn:
        rows = await conn.fetch(query, *query_args)
    return [{"tag": row["tag_item"], "count": row["count"]} for row in rows]

async def func_parent_read(*, client_postgres_pool: any, table: str, parent_column: str, parent_table: str, created_by_id: int, order: str, limit: int, page: int) -> list:
    """Read parent records based on child table's foreign key column (identifier validated)."""
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)):
        raise Exception(f"invalid identifier {table}")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(parent_column)):
        raise Exception(f"invalid identifier {parent_column}")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(parent_table)):
        raise Exception(f"invalid identifier {parent_table}")
    query = f"WITH x AS (SELECT {parent_column} FROM {table} WHERE ($1::bigint IS NULL OR created_by_id=$1) ORDER BY {order} LIMIT {limit} OFFSET {(page-1)*limit}) SELECT ct.* FROM x LEFT JOIN {parent_table} ct ON x.{parent_column}=ct.id;"
    async with client_postgres_pool.acquire() as conn:
        return [dict(r) for r in (await conn.fetch(query, created_by_id))]

async def func_postgres_clean(*, client_postgres_pool: any, config_table: dict) -> None:
    """Perform database maintenance by cleaning up expired records based on retention configurations (identifier validated)."""
    import re
    if not config_table:
        return None
    for tbl, cfg in config_table.items():
        if (retention_days := cfg.get("retention_day")) is not None:
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(tbl)):
                raise Exception(f"invalid identifier {tbl}")
            table = tbl
            query = f"DELETE FROM {table} WHERE created_at < NOW() - INTERVAL '{retention_days} days';"
            async with client_postgres_pool.acquire() as conn:
                await conn.execute(query)
    return None

async def func_postgres_map_column(*, client_postgres_pool: any, config_sql: str) -> dict:
    """Execute a SQL query and map results into a dictionary, supporting grouping for duplicate keys."""
    import re, orjson
    if not config_sql:
        return {}
    match = re.search(r"select\s+(.*?)\s+from\s", config_sql, flags=re.I | re.S)
    columns = [c.strip() for c in match.group(1).split(",")]
    key_col = columns[0]
    other_cols = columns[1:]
    result_map = {}
    async with client_postgres_pool.acquire() as conn:
        async with conn.transaction():
            async for record in conn.cursor(config_sql, prefetch=5000):
                key = record.get(key_col)
                if len(other_cols) == 1:
                    if other_cols[0] == "*":
                        val = dict(record)
                    else:
                        val = record.get(other_cols[0])
                else:
                    val = {c: record.get(c) for c in other_cols}
                if isinstance(val, str) and val.lstrip().startswith(("{", "[")):
                    try:
                        val = orjson.loads(val)
                    except Exception:
                        pass
                if key not in result_map:
                    result_map[key] = val
                else:
                    if not isinstance(result_map[key], list):
                        result_map[key] = [result_map[key]]
                    result_map[key].append(val)
    return result_map

async def func_postgres_runner(*, client_postgres_pool: any, mode: str, query: str) -> any:
    """Execute raw SQL queries in 'read' or 'write' mode with basic DDL and DELETE protection."""
    import re
    if mode != "read" and mode != "write":
        raise Exception(f"invalid mode: {mode}")
    ql = query.lower().strip()
    if re.search(r"\bdrop\b", ql):
        raise Exception("keyword drop forbidden")
    if re.search(r"\btruncate\b", ql):
        raise Exception("keyword truncate forbidden")
    if re.search(r"\bdelete\b", ql):
        raise Exception("keyword delete forbidden")
    if mode == "read" and not ql.startswith(("select", "with", "explain", "show", "describe")):
        raise Exception("read mode restricted to select/with/explain/show/describe")
    async with client_postgres_pool.acquire() as conn:
        if "returning" in ql:
            return await conn.fetch(query, timeout=15)
        return await conn.execute(query, timeout=15)

async def func_postgres_export(*, client_postgres_pool: any, query: str) -> any:
    """Stream PostgreSQL query results as a CSV Iterative Response with DDL and DELETE protection."""
    import re
    from fastapi.responses import StreamingResponse
    ql = query.lower().strip()
    if re.search(r"\bdrop\b", ql):
        raise Exception("keyword drop forbidden")
    if re.search(r"\btruncate\b", ql):
        raise Exception("keyword truncate forbidden")
    if re.search(r"\bdelete\b", ql):
        raise Exception("keyword delete forbidden")
    if not ql.startswith(("select", "with", "explain", "show", "describe")):
        raise Exception("export restricted to select/with/explain/show/describe")
    async def generate():
        async with client_postgres_pool.acquire() as conn:
            async with conn.transaction():
                is_first = 1
                async for record in conn.cursor(query):
                    if is_first == 1:
                        yield ",".join(record.keys()) + "\n"
                        is_first = 0
                    yield ",".join([f"\"{str(v).replace(chr(34), chr(34)*2)}\"" if v is not None else "" for v in record.values()]) + "\n"
    return StreamingResponse(generate(), media_type="text/csv")
