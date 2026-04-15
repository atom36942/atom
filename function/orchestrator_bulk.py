async def func_orchestrator_postgres_import(*, request: any, obj_form: dict) -> str:
    """Orchestrate bulk PostgreSQL data imports from CSV chunks with concurrency control and semaphore management."""
    import asyncio
    st, count, tasks, sem = request.app.state, 0, set(), asyncio.Semaphore(10)
    async def process_chunk(chunk_list):
       async with sem:
          if obj_form["mode"] == "create":
             await st.func_postgres_create(client_postgres_pool=st.client_postgres_pool, func_postgres_serialize=st.func_postgres_serialize, cache_postgres_schema=st.cache_postgres_schema, mode="now", table=obj_form["table"], obj_list=chunk_list, is_serialize=obj_form["is_serialize"], buffer_limit=0, cache_postgres_buffer=st.cache_postgres_buffer)
          elif obj_form["mode"] == "update":
             await st.func_postgres_update(client_postgres_pool=st.client_postgres_pool, func_postgres_serialize=st.func_postgres_serialize, cache_postgres_schema=st.cache_postgres_schema, table=obj_form["table"], obj_list=chunk_list, is_serialize=obj_form["is_serialize"], created_by_id=None, is_return_ids=0)
          elif obj_form["mode"] == "delete":
             await st.func_postgres_delete(client_postgres_pool=st.client_postgres_pool, table=obj_form["table"], ids=",".join(str(obj["id"]) for obj in chunk_list), created_by_id=None, config_postgres_ids_delete_limit=st.config_postgres_ids_delete_limit)
          return len(chunk_list)
    async for obj_list in st.func_api_file_to_chunks(upload_file=obj_form["file"][-1], chunk_size=st.config_limit_obj_list):
       if len(tasks) >= 20:
          done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
          for t in done: count += t.result()
       tasks.add(asyncio.create_task(process_chunk(obj_list)))
    if tasks:
       for res in await asyncio.gather(*tasks): count += res
    return f"{count} rows processed"

async def func_orchestrator_mongodb_import(*, request: any, obj_form: dict) -> str:
    """Orchestrate bulk MongoDB data imports from CSV chunks, supporting create and delete modes."""
    st, count = request.app.state, 0
    async for obj_list in st.func_api_file_to_chunks(upload_file=obj_form["file"][-1], chunk_size=st.config_limit_obj_list):
       if obj_form["mode"] == "create":
          await st.func_mongodb_object_create(client_mongodb=st.client_mongodb, database=obj_form["database"], table=obj_form["table"], obj_list=obj_list)
       elif obj_form["mode"] == "delete":
          await st.func_mongodb_object_delete(client_mongodb=st.client_mongodb, database=obj_form["database"], table=obj_form["table"], obj_list=obj_list)
       count += len(obj_list)
    return f"{count} rows processed"

async def func_orchestrator_redis_import(*, request: any, mode: str, obj_form: dict) -> str:
    """Orchestrate bulk Redis data operations from CSV chunks, supporting dynamic key mapping and TTL configuration."""
    st, count = request.app.state, 0
    async for obj_list in st.func_api_file_to_chunks(upload_file=obj_form["file"][-1], chunk_size=st.config_limit_obj_list):
       key_list = [f"""{obj_form["table"]}_{item["id"]}""" for item in obj_list]
       if mode == "create":
          await st.func_redis_object_create(client_redis=st.client_redis, keys=key_list, objects=obj_list, config_redis_cache_ttl_sec=obj_form.get("expiry_sec"))
       elif mode == "delete":
          await st.func_redis_object_delete(client_redis=st.client_redis, keys=key_list)
       count += len(obj_list)
    return f"{count} rows processed"
