# import stdlib
import asyncio

# import packages
import asyncpg
import boto3
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob.aio import BlobServiceClient

# import internal
from config import config_aws_access_key_id, config_aws_secret_access_key, config_azure_account_key, config_azure_account_name, config_postgres_url, config_s3_region_name, config_users_delete_batch_limit, config_users_delete_exclude_table, config_users_ownership_column, config_users_delete_retention_day, config_users_delete_retry_delay_sec, config_blob_purge_batch_limit, config_blob_purge_azure_concurrency

# logic
async def execute():
    print("Starting Users Delete Worker Script...")
    pool = await asyncpg.create_pool(dsn=config_postgres_url, min_size=1, max_size=5, server_settings={"application_name": "atom-daemon-users-delete"})
    clients = {"s3": None, "azure": None}
    if config_s3_region_name:
        clients["s3"] = boto3.client("s3", region_name=config_s3_region_name, aws_access_key_id=config_aws_access_key_id, aws_secret_access_key=config_aws_secret_access_key)
    if config_azure_account_name and config_azure_account_key:
        clients["azure"] = BlobServiceClient.from_connection_string(f"DefaultEndpointsProtocol=https;AccountName={config_azure_account_name};AccountKey={config_azure_account_key};EndpointSuffix=core.windows.net")
    def func_quote_ident(name: str) -> str:
        return '"' + name.replace('"', '""') + '"'
    def func_is_excluded_table(table: str) -> bool:
        for pattern in config_users_delete_exclude_table:
            if pattern.endswith("*"):
                if table.startswith(pattern[:-1]): return True
            elif table == pattern: return True
        return False
    def func_retry_delay_sec(retry_count: int) -> int:
        if not config_users_delete_retry_delay_sec: return 300
        index = min(max(retry_count, 0), len(config_users_delete_retry_delay_sec) - 1)
        return config_users_delete_retry_delay_sec[index]
    async def func_schema_columns(conn: asyncpg.Connection) -> dict:
        rows = await conn.fetch("SELECT c.table_name, c.column_name FROM information_schema.columns c JOIN information_schema.tables t ON c.table_name = t.table_name AND c.table_schema = t.table_schema WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE'")
        schema = {}
        for row in rows: schema.setdefault(row["table_name"], set()).add(row["column_name"])
        return schema
    def func_owned_tables(schema: dict) -> list:
        tables = []
        for table, columns in schema.items():
            if func_is_excluded_table(table): continue
            ownership_columns = [col for col in config_users_ownership_column if col in columns]
            if "deleted_at" not in columns or not ownership_columns: continue
            tables.append((table, ownership_columns, "is_protected" in columns))
        return tables
    async def func_claim_events(conn: asyncpg.Connection, batch_limit: int) -> list:
        return await conn.fetch("WITH claim AS (SELECT id FROM log_users_delete WHERE (((worker_status IN (1, 4) OR worker_status IS NULL) AND (worker_next_retry_at <= NOW() OR worker_next_retry_at IS NULL)) OR (worker_status = 2 AND updated_at < NOW() - INTERVAL '15 minutes')) ORDER BY created_at, id LIMIT $1 FOR UPDATE SKIP LOCKED) UPDATE log_users_delete l SET worker_status = 2, updated_at = NOW() FROM claim WHERE l.id = claim.id RETURNING l.id, l.user_id, l.event, l.worker_retry_count", batch_limit)
    async def func_mark_completed(conn: asyncpg.Connection, event_id: int) -> None:
        await conn.execute("UPDATE log_users_delete SET worker_status = 3, updated_at = NOW(), worker_processed_at = NOW(), worker_last_error = NULL WHERE id = $1", event_id)
    async def func_mark_failed(conn: asyncpg.Connection, event_id: int, retry_count: int, error: Exception) -> None:
        delay_sec = func_retry_delay_sec(retry_count)
        await conn.execute("UPDATE log_users_delete SET worker_status = 4, updated_at = NOW(), worker_retry_count = worker_retry_count + 1, worker_next_retry_at = NOW() + ($2 * INTERVAL '1 second'), worker_last_error = $3 WHERE id = $1", event_id, delay_sec, str(error)[:5000])
    async def func_set_deleted_at(conn: asyncpg.Connection, table: str, ownership_columns: list, has_is_protected: bool, user_id: int, value_sql: str, require_null: bool) -> int:
        table_sql = func_quote_ident(table)
        owner_where = " OR ".join(f"{func_quote_ident(col)} = $1" for col in ownership_columns)
        protected_where = ' AND ("is_protected" IS NULL OR "is_protected" IS FALSE)' if has_is_protected else ""
        null_where = ' AND "deleted_at" IS NULL' if require_null else ' AND "deleted_at" IS NOT NULL'
        result = await conn.execute(f'UPDATE {table_sql} SET "deleted_at" = {value_sql} WHERE ({owner_where}) {null_where} {protected_where}', user_id)
        return int(result.rsplit(" ", 1)[-1])
    async def func_purge_retained_rows(conn: asyncpg.Connection, table: str, has_is_protected: bool) -> int:
        table_sql = func_quote_ident(table)
        protected_where = ' AND ("is_protected" IS NULL OR "is_protected" IS FALSE)' if has_is_protected else ""
        result = await conn.execute(f'DELETE FROM {table_sql} WHERE ctid IN (SELECT ctid FROM {table_sql} WHERE "deleted_at" < NOW() - ($1 * INTERVAL \'1 day\') {protected_where} LIMIT 5000)', config_users_delete_retention_day)
        return int(result.rsplit(" ", 1)[-1])
    async def func_process_event(conn: asyncpg.Connection, event: asyncpg.Record, owned_tables: list) -> None:
        user_id = event["user_id"]
        event_type = event["event"]
        if event_type not in (1, 2, 3): raise Exception(f"invalid log_users_delete event: {event_type}")
        for table, ownership_columns, has_is_protected in owned_tables:
            if event_type == 1: await func_set_deleted_at(conn, table, ownership_columns, has_is_protected, user_id, "NOW()", True)
            elif event_type == 2: await func_set_deleted_at(conn, table, ownership_columns, has_is_protected, user_id, "NULL", False)
            elif event_type == 3: await func_set_deleted_at(conn, table, ownership_columns, has_is_protected, user_id, "NOW()", True)
    async def func_purge_retained_owned_rows(conn: asyncpg.Connection, owned_tables: list) -> int:
        total_deleted = 0
        for table, _ownership_columns, has_is_protected in owned_tables:
            if table == "blob": continue
            deleted_count = -1
            while deleted_count != 0:
                deleted_count = await func_purge_retained_rows(conn, table, has_is_protected)
                total_deleted += deleted_count
                if deleted_count: await asyncio.sleep(0.05)
        return total_deleted
    async def func_delete_blob_storage(rows: list) -> None:
        s3_batches = {}
        azure_tasks = []
        for row in rows:
            service, container, blob_key = row["service"], row["container"], row["blob_key"]
            if service == "s3":
                if not clients.get("s3"): raise Exception("S3 client is not configured for blob purge")
                s3_batches.setdefault(container, []).append({"Key": blob_key})
            elif service == "azure":
                if not clients.get("azure"): raise Exception("Azure blob client is not configured for blob purge")
                azure_tasks.append(clients["azure"].get_blob_client(container=container, blob=blob_key).delete_blob())
            else:
                raise Exception(f"unsupported blob service: {service}")
        for bucket, keys in s3_batches.items():
            for i in range(0, len(keys), 1000):
                response = await asyncio.to_thread(clients["s3"].delete_objects, Bucket=bucket, Delete={"Objects": keys[i:i+1000], "Quiet": True})
                if response.get("Errors"): raise Exception(f"S3 blob delete failed: {response['Errors'][:3]}")
        for i in range(0, len(azure_tasks), config_blob_purge_azure_concurrency):
            results = await asyncio.gather(*azure_tasks[i:i+config_blob_purge_azure_concurrency], return_exceptions=True)
            for result in results:
                if isinstance(result, ResourceNotFoundError): continue
                if isinstance(result, Exception): raise result
    async def func_purge_retained_blob_rows(conn: asyncpg.Connection) -> int:
        total_deleted = 0
        deleted_count = -1
        while deleted_count != 0:
            rows = await conn.fetch('SELECT id, service, container, blob_key FROM "blob" WHERE "deleted_at" < NOW() - ($1 * INTERVAL \'1 day\') LIMIT $2', config_users_delete_retention_day, config_blob_purge_batch_limit)
            if not rows:
                deleted_count = 0
                continue
            await func_delete_blob_storage(rows)
            result = await conn.execute('DELETE FROM "blob" WHERE id = ANY($1::bigint[]) AND "deleted_at" < NOW() - ($2 * INTERVAL \'1 day\')', [row["id"] for row in rows], config_users_delete_retention_day)
            deleted_count = int(result.rsplit(" ", 1)[-1])
            total_deleted += deleted_count
            if deleted_count: await asyncio.sleep(0.05)
        return total_deleted
    async def func_users_delete_worker_once() -> int:
        async with pool.acquire() as conn:
            schema = await func_schema_columns(conn)
            owned_tables = func_owned_tables(schema)
            async with conn.transaction():
                events = await func_claim_events(conn, config_users_delete_batch_limit)
        if events: print(f"[users-delete-worker] claimed {len(events)} event(s)")
        for event in events:
            async with pool.acquire() as event_conn:
                try:
                    async with event_conn.transaction():
                        await func_process_event(event_conn, event, owned_tables)
                        await func_mark_completed(event_conn, event["id"])
                    print(f"[users-delete-worker] completed event_id={event['id']} user_id={event['user_id']} event={event['event']}")
                except Exception as exc:
                    async with event_conn.transaction():
                        await func_mark_failed(event_conn, event["id"], event["worker_retry_count"], exc)
                    print(f"[users-delete-worker] failed event_id={event['id']} user_id={event['user_id']} event={event['event']} error={str(exc)[:300]}")
        async with pool.acquire() as purge_conn:
            purged = await func_purge_retained_owned_rows(purge_conn, owned_tables)
            if any(table == "blob" for table, _ownership_columns, _has_is_protected in owned_tables):
                purged += await func_purge_retained_blob_rows(purge_conn)
            if purged: print(f"[users-delete-worker] purged {purged} retained deleted row(s)")
        return len(events)
    try:
        idle_count = 0
        while True:
            processed = await func_users_delete_worker_once()
            if processed:
                idle_count = 0
                await asyncio.sleep(1)
            else:
                idle_count += 1
                if idle_count == 1 or idle_count % 12 == 0:
                    print("[users-delete-worker] no pending events; sleeping...")
                await asyncio.sleep(5)
    finally:
        if clients.get("azure"): await clients["azure"].close()
        await pool.close()

# init
if __name__ == "__main__":
    asyncio.run(execute())
