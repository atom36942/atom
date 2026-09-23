"""Atom data import functions."""

from .files import func_api_file_to_chunks

async def func_redis_import(*, client_redis: any, config_redis_cache_ttl_sec: int, mode: str, file: any) -> str:
    """Imports or deletes keys in Redis in batches from a CSV file."""
    import orjson
    if not client_redis: raise Exception("redis client not initialized")
    count = 0; limit_batch = 5000
    async for ol in func_api_file_to_chunks(upload_file=file, chunk_size=limit_batch):
        if mode == "create":
            if sorted(list(ol[0].keys())) != sorted(["key", "value"]): raise Exception("CSV format error: requires 'key' and 'value'")
            async with client_redis.pipeline(transaction=False) as pipe:
                for item in ol:
                    val = orjson.dumps(item["value"]).decode("utf-8")
                    if config_redis_cache_ttl_sec: pipe.setex(item["key"], config_redis_cache_ttl_sec, val)
                    else: pipe.set(item["key"], val)
                await pipe.execute()
        elif mode == "delete":
            if list(ol[0].keys()) != ["key"]: raise Exception("CSV format error: requires 'key' column")
            async with client_redis.pipeline(transaction=False) as pipe:
                pipe.delete(*[item["key"] for item in ol])
                await pipe.execute()
        count += len(ol)
    return f"{count} rows processed"

async def func_mongodb_import(*, client_mongodb: any, mode: str, database: str, table: str, file: any) -> str:
    """Imports, updates, or deletes records in MongoDB from a CSV upload file in batches."""
    from pymongo import UpdateOne, DeleteOne
    if not client_mongodb: raise Exception("mongodb client not initialized")
    count = 0
    limit_batch = 5000
    collection = client_mongodb[database][table]
    def _mongodb_import_id(item, mode_name):
        if "id" not in item and "_id" not in item: raise Exception(f"CSV format error: MongoDB {mode_name} requires 'id' or '_id' column")
        oid = item.get("id") or item.get("_id")
        if not oid: raise Exception(f"CSV format error: MongoDB {mode_name} requires non-empty 'id' or '_id'")
        return oid
    async for ol in func_api_file_to_chunks(upload_file=file, chunk_size=limit_batch):
        if not ol: continue
        if mode == "create":
            await collection.insert_many(ol)
        elif mode == "update":
            operations = []
            for item in ol:
                oid = _mongodb_import_id(item, mode)
                item = dict(item)
                item.pop("id", None); item.pop("_id", None)
                operations.append(UpdateOne({"_id": oid}, {"$set": item}))
            await collection.bulk_write(operations, ordered=True)
        elif mode == "delete":
            operations = [DeleteOne({"_id": _mongodb_import_id(item, mode)}) for item in ol]
            await collection.bulk_write(operations, ordered=True)
        count += len(ol)
    return f"{count} rows processed"

async def func_postgres_import(*, app_state: any, mode: str, table: str, file: any, client_postgres: any = None, cache_postgres_schema: dict = None) -> str:
    """Imports, updates, or deletes records in PostgreSQL from a CSV upload file in batches."""
    client_postgres = client_postgres or app_state.client_postgres
    cache_postgres_schema = cache_postgres_schema if cache_postgres_schema is not None else app_state.cache_postgres_schema
    if not client_postgres: raise Exception("postgres client not initialized")
    if mode == "delete": app_state.func_check_user_delete_permission(app_state=app_state, table=table, scope="admin")
    count = 0
    async with client_postgres.acquire() as conn:
        async with conn.transaction():
            async for ol in func_api_file_to_chunks(upload_file=file, chunk_size=5000):
                if not ol: continue
                if mode in ("update", "delete") and any("id" not in obj for obj in ol): raise Exception(f"CSV format error: Postgres {mode} requires 'id' column")
                if mode == "create":
                    await app_state.func_postgres_create(client_postgres=client_postgres, client_postgres_conn=conn, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=cache_postgres_schema, cache_postgres_buffer=app_state.cache_postgres_buffer_create, config_column_regex=app_state.config_column_regex, buffer_limit=app_state.config_buffer_limit_default, mode="now", table=table, obj_list=ol)
                elif mode == "update":
                    await app_state.func_postgres_update(client_postgres=client_postgres, client_postgres_conn=conn, client_password_hasher=app_state.client_password_hasher, func_postgres_serialize=app_state.func_postgres_serialize, func_regex_check=app_state.func_regex_check, cache_postgres_schema=cache_postgres_schema, config_column_regex=app_state.config_column_regex, table=table, obj_list=ol, created_by_id=None)
                elif mode == "delete":
                    await app_state.func_postgres_delete(client_postgres=client_postgres, client_postgres_conn=conn, cache_postgres_schema=cache_postgres_schema, table=table, ids=[obj["id"] for obj in ol], created_by_id=None)
                count += len(ol)
    return f"{count} rows processed"
