async def func_orchestrator_postgres_import(*, upload_file: any, mode: str, table: str, is_serialize: int, config_regex: dict, func_regex_check: callable, client_postgres_pool: any, client_password_hasher: any, cache_postgres_schema: dict, cache_postgres_buffer: dict, func_postgres_serialize: callable, func_postgres_create: callable, func_postgres_update: callable, func_postgres_delete: callable, func_api_file_to_chunks: callable) -> int:
    """Orchestrates atomic bulk PostgreSQL operations using a single transaction to ensure data integrity."""
    limit_chunk = 5000
    if mode == "update" and is_serialize == 0:
        raise Exception("is_serialize=1 is mandatory for update mode")
    count = 0
    first_chunk = True
    async with client_postgres_pool.acquire() as conn:
        async with conn.transaction():
            async for obj_list in func_api_file_to_chunks(upload_file=upload_file, chunk_size=limit_chunk):
                if first_chunk:
                    if mode in ("update", "delete") and "id" not in obj_list[0]:
                        raise Exception(f"CSV format error: Postgres {mode} requires 'id' column")
                    first_chunk = False
                if table == "users":
                    await func_regex_check(config_regex=config_regex, obj_list=obj_list)
                if mode == "create":
                    await func_postgres_create(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, mode="now", table=table, obj_list=obj_list, is_serialize=is_serialize, buffer_limit=0, cache_postgres_buffer=cache_postgres_buffer, client_postgres_conn=conn)
                elif mode == "update":
                    await func_postgres_update(client_postgres_pool=client_postgres_pool, client_password_hasher=client_password_hasher, func_postgres_serialize=func_postgres_serialize, cache_postgres_schema=cache_postgres_schema, table=table, obj_list=obj_list, is_serialize=is_serialize, created_by_id=None, is_return_ids=0, client_postgres_conn=conn)
                elif mode == "delete":
                    await func_postgres_delete(client_postgres_pool=client_postgres_pool, table=table, ids=",".join(str(obj["id"]) for obj in obj_list), created_by_id=None, client_postgres_conn=conn)
                count += len(obj_list)
    return count
