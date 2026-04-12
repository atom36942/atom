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

async def func_ids_delete(*, client_postgres_pool: any, table: str, ids: any, created_by_id: int = None, config_postgres_ids_delete_limit: int = 1000) -> str:
    """Delete records by ID with optional ownership and system table restrictions (identifier validated)."""
    import re
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)):
        raise Exception(f"invalid identifier {table}")
    if table == "users":
        raise Exception("users table not allowed")
    ids_str = ""
    if isinstance(ids, str):
        id_list = [str(int(x.strip())) for x in ids.split(",") if x.strip()]
        if len(id_list) > config_postgres_ids_delete_limit:
            raise Exception("ids length exceeded")
        ids_str = ",".join(id_list)
    elif isinstance(ids, (list, tuple)):
        if len(ids) > config_postgres_ids_delete_limit:
            raise Exception("ids length exceeded")
        ids_str = ",".join([str(int(x)) for x in ids])
    delete_query = f"DELETE FROM {table} WHERE id IN ({ids_str}) AND ($1::bigint IS NULL OR created_by_id=$1);"
    if table == "spatial_ref_sys":
        raise Exception("system table protected")
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(delete_query, created_by_id)
    return "ids deleted"

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