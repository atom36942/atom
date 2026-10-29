# command: venv/bin/python -m script.worker_users_delete

# info: Permanently hard-deletes soft-deleted user data and its storage files after the data retention window expires.

# import
import asyncio
import urllib.parse
import asyncpg
import boto3
from azure.core.exceptions import ResourceNotFoundError
from function import func_client_postgres
from function import func_client_azure_blob

# config
from config import config_postgres_url_dict
from config import config_aws_access_key_id
from config import config_aws_secret_access_key
from config import config_azure_account_key
from config import config_azure_account_name
from config import config_aws_s3_region_name
from config import config_table_exclude_from_users_delete
from config import config_column_ownership_delete
from config import config_users_delete_retention_day
postgres_url_master = config_postgres_url_dict.get("master")

# setting
USERS_DELETE_BATCH_LIMIT = 100
WORKER_RETRY_DELAY_SEC = [60, 300, 900, 3600, 21600]
BLOB_PURGE_BATCH_LIMIT = 5000
BLOB_PURGE_AZURE_CONCURRENCY = 256
POLL_INTERVAL_SEC = 5

# logic
def ident_quote(*, name: str) -> str:
    return '"' + name.replace('"', '""') + '"'

def retry_delay_sec(*, retry_count: int) -> int:
    return WORKER_RETRY_DELAY_SEC[min(max(retry_count, 0), len(WORKER_RETRY_DELAY_SEC) - 1)]

def storage_client_open(*, aws_region: str, aws_key_id: str, aws_secret: str, azure_name: str, azure_key: str) -> dict:
    clients = {"s3": None, "azure": None}
    if aws_region: clients["s3"] = boto3.client("s3", region_name=aws_region, aws_access_key_id=aws_key_id, aws_secret_access_key=aws_secret)
    if azure_name and azure_key: clients["azure"] = func_client_azure_blob(account_name=azure_name, account_key=azure_key)
    return clients

async def schema_column_read(*, conn: asyncpg.Connection) -> dict:
    rows = await conn.fetch("SELECT c.table_name, c.column_name FROM information_schema.columns c JOIN information_schema.tables t ON c.table_name = t.table_name AND c.table_schema = t.table_schema WHERE c.table_schema = 'public' AND t.table_type = 'BASE TABLE'")
    schema = {}
    for row in rows: schema.setdefault(row["table_name"], set()).add(row["column_name"])
    return schema

def owned_table_list(*, schema: dict, table_exclude: list, ownership_column_list: list) -> list:
    """(table, ownership columns, has is_protected) for every table a user's rows can be soft-deleted in."""
    tables = []
    for table, columns in schema.items():
        if table in table_exclude: continue
        ownership_columns = [col for col in ownership_column_list if col in columns]
        if "deleted_at" not in columns or not ownership_columns: continue
        tables.append((table, ownership_columns, "is_protected" in columns))
    return tables

async def task_claim(*, conn: asyncpg.Connection, batch_limit: int) -> list:
    return await conn.fetch("WITH claim AS (SELECT id FROM log_users_delete WHERE (worker_status IS NULL OR worker_status IN (1, 3)) AND (worker_next_retry_at <= NOW() OR worker_next_retry_at IS NULL) ORDER BY created_at, id LIMIT $1 FOR UPDATE SKIP LOCKED) UPDATE log_users_delete l SET worker_status = 1, worker_next_retry_at = NOW() + INTERVAL '15 minutes' FROM claim WHERE l.id = claim.id RETURNING l.id, l.user_id, l.type, l.worker_retry_count", batch_limit)

async def task_complete(*, conn: asyncpg.Connection, task_id: int) -> None:
    await conn.execute("UPDATE log_users_delete SET worker_status = 2, worker_processed_at = NOW(), worker_last_error = NULL WHERE id = $1", task_id)

async def task_fail(*, conn: asyncpg.Connection, task_id: int, retry_count: int, error: Exception) -> None:
    if retry_count >= len(WORKER_RETRY_DELAY_SEC):
        await conn.execute("UPDATE log_users_delete SET worker_status = 4, worker_retry_count = worker_retry_count + 1, worker_last_error = $2 WHERE id = $1", task_id, str(error)[:5000])
    else:
        await conn.execute("UPDATE log_users_delete SET worker_status = 3, worker_retry_count = worker_retry_count + 1, worker_next_retry_at = NOW() + ($2 * INTERVAL '1 second'), worker_last_error = $3 WHERE id = $1", task_id, retry_delay_sec(retry_count=retry_count), str(error)[:5000])

async def deleted_at_set(*, conn: asyncpg.Connection, table: str, ownership_columns: list, has_is_protected: bool, user_id: int, value_sql: str, require_null: bool) -> int:
    table_sql = ident_quote(name=table)
    owner_where = " OR ".join(f"{ident_quote(name=col)} = $1" for col in ownership_columns)
    protected_where = ' AND ("is_protected" IS NULL OR "is_protected" IS FALSE)' if has_is_protected else ""
    null_where = ' AND "deleted_at" IS NULL' if require_null else ' AND "deleted_at" IS NOT NULL'
    result = await conn.execute(f'UPDATE {table_sql} SET "deleted_at" = {value_sql} WHERE ({owner_where}) {null_where} {protected_where}', user_id)  # noqa: S608 - identifiers quoted by ident_quote, value is NOW() or NULL
    return int(result.rsplit(" ", 1)[-1])

async def task_process(*, conn: asyncpg.Connection, task: asyncpg.Record, owned_tables: list) -> None:
    """Type 1 and 3 soft-delete the user's rows, type 2 restores them."""
    if task["type"] not in (1, 2, 3): raise Exception(f"invalid log_users_delete type: {task['type']}")
    value_sql, require_null = ("NULL", False) if task["type"] == 2 else ("NOW()", True)
    for table, ownership_columns, has_is_protected in owned_tables:
        await deleted_at_set(conn=conn, table=table, ownership_columns=ownership_columns, has_is_protected=has_is_protected, user_id=task["user_id"], value_sql=value_sql, require_null=require_null)

async def retained_row_purge(*, conn: asyncpg.Connection, table: str, has_is_protected: bool, retention_day: int) -> int:
    table_sql = ident_quote(name=table)
    protected_where = ' AND ("is_protected" IS NULL OR "is_protected" IS FALSE)' if has_is_protected else ""
    result = await conn.execute(f'DELETE FROM {table_sql} WHERE ctid IN (SELECT ctid FROM {table_sql} WHERE "deleted_at" < NOW() - ($1 * INTERVAL \'1 day\') {protected_where} LIMIT 5000)', retention_day)  # noqa: S608 - identifiers quoted by ident_quote
    return int(result.rsplit(" ", 1)[-1])

async def retained_owned_row_purge(*, conn: asyncpg.Connection, owned_tables: list, retention_day: int) -> int:
    total_deleted = 0
    for table, _ownership_columns, has_is_protected in owned_tables:
        if table == "blob": continue
        while (deleted_count := await retained_row_purge(conn=conn, table=table, has_is_protected=has_is_protected, retention_day=retention_day)):
            total_deleted += deleted_count
            await asyncio.sleep(0.05)
    return total_deleted

async def blob_storage_delete(*, rows: list, clients: dict) -> None:
    s3_batches, azure_tasks = {}, []
    for row in rows:
        service, file_url = row["service"], row["file_url"]
        if service == "s3":
            if not clients["s3"]: raise Exception("S3 client is not configured for blob purge")
            bucket = file_url.split("//", 1)[1].split(".", 1)[0]
            s3_batches.setdefault(bucket, []).append({"Key": urllib.parse.unquote(file_url.split(".com/", 1)[1])})
        elif service == "azure":
            if not clients["azure"]: raise Exception("Azure blob client is not configured for blob purge")
            container, blob_key = file_url.split(".net/", 1)[1].split("/", 1)
            azure_tasks.append(clients["azure"].get_blob_client(container=container, blob=urllib.parse.unquote(blob_key)).delete_blob())
        else:
            raise Exception(f"unsupported blob service: {service}")
    for bucket, keys in s3_batches.items():
        for i in range(0, len(keys), 1000):
            response = await asyncio.to_thread(clients["s3"].delete_objects, Bucket=bucket, Delete={"Objects": keys[i:i+1000], "Quiet": True})
            if response.get("Errors"): raise Exception(f"S3 blob delete failed: {response['Errors'][:3]}")
    for i in range(0, len(azure_tasks), BLOB_PURGE_AZURE_CONCURRENCY):
        for result in await asyncio.gather(*azure_tasks[i:i+BLOB_PURGE_AZURE_CONCURRENCY], return_exceptions=True):
            if isinstance(result, Exception) and not isinstance(result, ResourceNotFoundError): raise result

async def retained_blob_row_purge(*, conn: asyncpg.Connection, clients: dict, retention_day: int) -> int:
    """Deletes the stored file first, then its blob row, so no file is left without a row pointing at it."""
    total_deleted = 0
    while (rows := await conn.fetch('SELECT id, service, file_url FROM "blob" WHERE "deleted_at" < NOW() - ($1 * INTERVAL \'1 day\') LIMIT $2', retention_day, BLOB_PURGE_BATCH_LIMIT)):
        await blob_storage_delete(rows=rows, clients=clients)
        result = await conn.execute('DELETE FROM "blob" WHERE id = ANY($1::bigint[]) AND "deleted_at" < NOW() - ($2 * INTERVAL \'1 day\')', [row["id"] for row in rows], retention_day)
        deleted_count = int(result.rsplit(" ", 1)[-1])
        if not deleted_count: break
        total_deleted += deleted_count
        await asyncio.sleep(0.05)
    return total_deleted

async def worker_run_once(*, pool, clients: dict, table_exclude: list, ownership_column_list: list, retention_day: int) -> int:
    """Claims and processes one batch of tasks, then purges rows past the retention window; returns the tasks claimed."""
    async with pool.acquire() as conn:
        owned_tables = owned_table_list(schema=await schema_column_read(conn=conn), table_exclude=table_exclude, ownership_column_list=ownership_column_list)
        async with conn.transaction(): tasks = await task_claim(conn=conn, batch_limit=USERS_DELETE_BATCH_LIMIT)
    if tasks: print(f"[users-delete-worker] claimed {len(tasks)} task(s)")
    for task in tasks:
        label = f"task_id={task['id']} user_id={task['user_id']} type={task['type']}"
        async with pool.acquire() as conn:
            try:
                async with conn.transaction():
                    await task_process(conn=conn, task=task, owned_tables=owned_tables)
                    await task_complete(conn=conn, task_id=task["id"])
                print(f"[users-delete-worker] completed {label}")
            except Exception as exc:
                async with conn.transaction(): await task_fail(conn=conn, task_id=task["id"], retry_count=task["worker_retry_count"], error=exc)
                print(f"[users-delete-worker] failed {label} error={str(exc)[:300]}")
    async with pool.acquire() as conn:
        purged = await retained_owned_row_purge(conn=conn, owned_tables=owned_tables, retention_day=retention_day)
        if any(table == "blob" for table, *_ in owned_tables): purged += await retained_blob_row_purge(conn=conn, clients=clients, retention_day=retention_day)
    if purged: print(f"[users-delete-worker] purged {purged} retained deleted row(s)")
    return len(tasks)

async def worker_loop(*, postgres_url, storage, table_exclude, ownership_column_list, retention_day):
    pool = await func_client_postgres(dsn=postgres_url, min_size=1, max_size=5)
    clients = storage_client_open(**storage)
    try:
        idle_count = 0
        while True:
            if await worker_run_once(pool=pool, clients=clients, table_exclude=table_exclude, ownership_column_list=ownership_column_list, retention_day=retention_day):
                idle_count = 0
                await asyncio.sleep(1)
                continue
            idle_count += 1
            if idle_count == 1 or idle_count % 12 == 0: print("[users-delete-worker] no pending tasks; sleeping...")
            await asyncio.sleep(POLL_INTERVAL_SEC)
    finally:
        if clients["azure"]: await clients["azure"].close()
        await pool.close()

def main():
    print("Starting Users Delete Worker Script...")
    storage = {"aws_region": config_aws_s3_region_name, "aws_key_id": config_aws_access_key_id, "aws_secret": config_aws_secret_access_key, "azure_name": config_azure_account_name, "azure_key": config_azure_account_key}
    asyncio.run(worker_loop(postgres_url=postgres_url_master, storage=storage, table_exclude=config_table_exclude_from_users_delete, ownership_column_list=config_column_ownership_delete, retention_day=config_users_delete_retention_day))

# main
if __name__ == "__main__":
    main()
