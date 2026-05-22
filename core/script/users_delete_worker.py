#import
import asyncio
import asyncpg

#config
from core.config import (
    config_postgres_url,
    config_users_delete_batch_limit,
    config_users_delete_exclude_table,
    config_users_delete_ownership_column,
    config_users_delete_retention_day,
    config_users_delete_retry_delay_sec,
)

#func
def func_quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'

def func_is_excluded_table(table: str) -> bool:
    for pattern in config_users_delete_exclude_table:
        if pattern.endswith("*"):
            if table.startswith(pattern[:-1]):
                return True
        elif table == pattern:
            return True
    return False

def func_retry_delay_sec(retry_count: int) -> int:
    if not config_users_delete_retry_delay_sec:
        return 300
    index = min(max(retry_count, 0), len(config_users_delete_retry_delay_sec) - 1)
    return config_users_delete_retry_delay_sec[index]

async def func_schema_columns(conn: asyncpg.Connection) -> dict:
    rows = await conn.fetch(
        """
        SELECT c.table_name, c.column_name
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON c.table_name = t.table_name
         AND c.table_schema = t.table_schema
        WHERE c.table_schema = 'public'
          AND t.table_type = 'BASE TABLE'
        """
    )
    schema = {}
    for row in rows:
        schema.setdefault(row["table_name"], set()).add(row["column_name"])
    return schema

def func_owned_tables(schema: dict) -> list:
    tables = []
    for table, columns in schema.items():
        if func_is_excluded_table(table):
            continue
        ownership_columns = [col for col in config_users_delete_ownership_column if col in columns]
        if "deleted_at" not in columns or not ownership_columns:
            continue
        tables.append((table, ownership_columns, "is_protected" in columns))
    return tables

async def func_claim_events(conn: asyncpg.Connection, batch_limit: int) -> list:
    return await conn.fetch(
        """
        WITH claim AS (
            SELECT id
            FROM log_users_delete
            WHERE status IN (1,4)
              AND next_retry_at <= NOW()
            ORDER BY created_at, id
            LIMIT $1
            FOR UPDATE SKIP LOCKED
        )
        UPDATE log_users_delete l
        SET status = 2,
            updated_at = NOW()
        FROM claim
        WHERE l.id = claim.id
        RETURNING l.id, l.user_id, l.event, l.retry_count
        """,
        batch_limit,
    )

async def func_mark_completed(conn: asyncpg.Connection, event_id: int) -> None:
    await conn.execute(
        """
        UPDATE log_users_delete
        SET status = 3,
            updated_at = NOW(),
            processed_at = NOW(),
            last_error = NULL
        WHERE id = $1
        """,
        event_id,
    )

async def func_mark_failed(conn: asyncpg.Connection, event_id: int, retry_count: int, error: Exception) -> None:
    delay_sec = func_retry_delay_sec(retry_count)
    await conn.execute(
        """
        UPDATE log_users_delete
        SET status = 4,
            updated_at = NOW(),
            retry_count = retry_count + 1,
            next_retry_at = NOW() + ($2 * INTERVAL '1 second'),
            last_error = $3
        WHERE id = $1
        """,
        event_id,
        delay_sec,
        str(error)[:5000],
    )

async def func_set_deleted_at(conn: asyncpg.Connection, table: str, ownership_columns: list, has_is_protected: bool, user_id: int, value_sql: str, require_null: bool) -> int:
    table_sql = func_quote_ident(table)
    owner_where = " OR ".join(f"{func_quote_ident(col)} = $1" for col in ownership_columns)
    protected_where = ' AND ("is_protected" IS NULL OR "is_protected" IS FALSE)' if has_is_protected else ""
    null_where = ' AND "deleted_at" IS NULL' if require_null else ' AND "deleted_at" IS NOT NULL'
    sql = f"""
        UPDATE {table_sql}
        SET "deleted_at" = {value_sql}
        WHERE ({owner_where})
        {null_where}
        {protected_where}
    """
    result = await conn.execute(sql, user_id)
    return int(result.rsplit(" ", 1)[-1])

async def func_purge_retained_rows(conn: asyncpg.Connection, table: str, has_is_protected: bool) -> int:
    table_sql = func_quote_ident(table)
    protected_where = ' AND ("is_protected" IS NULL OR "is_protected" IS FALSE)' if has_is_protected else ""
    sql = f"""
        DELETE FROM {table_sql}
        WHERE ctid IN (
            SELECT ctid
            FROM {table_sql}
            WHERE "deleted_at" < NOW() - ($1 * INTERVAL '1 day')
            {protected_where}
            LIMIT 5000
        )
    """
    result = await conn.execute(sql, config_users_delete_retention_day)
    return int(result.rsplit(" ", 1)[-1])

async def func_process_event(conn: asyncpg.Connection, event: asyncpg.Record, owned_tables: list) -> None:
    user_id = event["user_id"]
    event_type = event["event"]
    if event_type not in (1, 2, 3):
        raise Exception(f"invalid log_users_delete event: {event_type}")
    for table, ownership_columns, has_is_protected in owned_tables:
        if event_type == 1:
            await func_set_deleted_at(conn, table, ownership_columns, has_is_protected, user_id, "NOW()", True)
        elif event_type == 2:
            await func_set_deleted_at(conn, table, ownership_columns, has_is_protected, user_id, "NULL", False)
        elif event_type == 3:
            await func_set_deleted_at(conn, table, ownership_columns, has_is_protected, user_id, "NOW()", True)

async def func_purge_retained_owned_rows(conn: asyncpg.Connection, owned_tables: list) -> int:
    total_deleted = 0
    for table, _ownership_columns, has_is_protected in owned_tables:
        deleted_count = -1
        while deleted_count != 0:
            deleted_count = await func_purge_retained_rows(conn, table, has_is_protected)
            total_deleted += deleted_count
            if deleted_count:
                await asyncio.sleep(0.05)
    return total_deleted

async def func_users_delete_worker_once(pool: asyncpg.Pool) -> int:
    async with pool.acquire() as conn:
        schema = await func_schema_columns(conn)
        owned_tables = func_owned_tables(schema)
        async with conn.transaction():
            events = await func_claim_events(conn, config_users_delete_batch_limit)
        if events:
            print(f"[users-delete-worker] claimed {len(events)} event(s)")
        for event in events:
            async with pool.acquire() as event_conn:
                try:
                    async with event_conn.transaction():
                        await func_process_event(event_conn, event, owned_tables)
                        await func_mark_completed(event_conn, event["id"])
                    print(f"[users-delete-worker] completed event_id={event['id']} user_id={event['user_id']} event={event['event']}")
                except Exception as exc:
                    async with event_conn.transaction():
                        await func_mark_failed(event_conn, event["id"], event["retry_count"], exc)
                    print(f"[users-delete-worker] failed event_id={event['id']} user_id={event['user_id']} event={event['event']} error={str(exc)[:300]}")
        async with pool.acquire() as purge_conn:
            purged = await func_purge_retained_owned_rows(purge_conn, owned_tables)
            if purged:
                print(f"[users-delete-worker] purged {purged} retained deleted row(s)")
        return len(events)

async def func_users_delete_worker():
    if not config_postgres_url:
        print("Error: config_postgres_url is not set in environment or config.")
        return
    print("Starting Users Delete Worker Daemon...")
    pool = await asyncpg.create_pool(dsn=config_postgres_url, min_size=1, max_size=5, server_settings={"application_name": "atom-daemon-users-delete"})
    try:
        idle_count = 0
        while True:
            processed = await func_users_delete_worker_once(pool)
            if processed:
                idle_count = 0
                await asyncio.sleep(1)
            else:
                idle_count += 1
                if idle_count == 1 or idle_count % 12 == 0:
                    print("[users-delete-worker] no pending events; sleeping")
                await asyncio.sleep(5)
    finally:
        await pool.close()

#init
if __name__ == "__main__":
    asyncio.run(func_users_delete_worker())
