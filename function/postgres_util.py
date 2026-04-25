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

