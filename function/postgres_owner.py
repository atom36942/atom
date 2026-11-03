# import
import asyncio
import re
import asyncpg
from .middleware import func_api_error

# function
async def func_postgres_delete_all(*, client_postgres: asyncpg.Pool | None, client_postgres_conn: asyncpg.Connection | None = None, cache_postgres_schema: dict = None, table: str, ownership_column: str, user_id: int, limit: int = 5000) -> dict:
    """Delete records in a table matching an ownership column for a user in safe batches."""
    if not client_postgres and not client_postgres_conn: raise func_api_error(message="postgres client not initialized", status_code=500)
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(table)): raise Exception(f"invalid identifier {table}")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(ownership_column)): raise Exception(f"invalid identifier {ownership_column}")
    if table == "spatial_ref_sys": raise Exception("system table protected")
    if cache_postgres_schema is not None and table not in cache_postgres_schema: raise Exception(f"table '{table}' not found")
    schema = (cache_postgres_schema or {}).get(table, {})
    if schema and ownership_column not in schema: raise Exception(f"table '{table}' lacks required '{ownership_column}' column")
    id_col = '"id"' if (not schema or "id" in schema) else "ctid"
    batch_limit = limit if limit and limit > 0 else 5000
    async def _execute_delete_all(connection):
        sql = f'WITH to_delete AS (SELECT {id_col} FROM "{table}" WHERE "{ownership_column}"=$1 LIMIT $2) DELETE FROM "{table}" WHERE {id_col} IN (SELECT {id_col} FROM to_delete)'  # noqa: S608 - identifiers pattern-checked and quoted, values bound as $n
        result = await connection.execute(sql, user_id, batch_limit)
        deleted_count = int(result.rsplit(" ", 1)[-1])
        if deleted_count < batch_limit:
            has_more = False
        else:
            has_more = bool(await connection.fetchval(f'SELECT EXISTS(SELECT 1 FROM "{table}" WHERE "{ownership_column}"=$1 LIMIT 1)', user_id))  # noqa: S608 - identifiers pattern-checked and quoted, values bound as $n
        return {"deleted_count": deleted_count, "has_more": has_more, "has_next_page": has_more}
    if client_postgres_conn:
        return await _execute_delete_all(client_postgres_conn)
    async with client_postgres.acquire() as conn:
        return await _execute_delete_all(conn)

def func_postgres_mark_read(*, client_postgres: asyncpg.Pool | None, table: str, ownership_column: str, user_id: int, ids: list) -> None:
    """Schedule a non-blocking read_at update for fetched objects owned by a user."""
    if not ids: return
    for identifier in (table, ownership_column):
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(identifier)): raise Exception(f"invalid identifier {identifier}")
    read_ids = list(dict.fromkeys(int(obj_id) for obj_id in ids if obj_id is not None))
    if not read_ids: return
    async def update_read_at():
        async with client_postgres.acquire() as conn:
            await conn.execute(f'UPDATE "{table}" SET read_at=now() WHERE "{ownership_column}"=$1 AND "id"=ANY($2::bigint[]) AND read_at IS NULL', user_id, read_ids)  # noqa: S608 - identifiers pattern-checked and quoted, values bound as $n
    task = asyncio.create_task(update_read_at())
    task.add_done_callback(lambda t: (t.exception() if not t.cancelled() else None))
    return
