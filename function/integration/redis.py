async def func_redis_create(*, upload_file: any, client_redis: any, chunk_size: int, config_redis_cache_ttl_sec: int, func_api_file_to_chunks: any) -> int:
    """Batch create/update objects in Redis from an uploaded CSV file."""
    import orjson
    count, first_chunk = 0, True
    async for ol in func_api_file_to_chunks(upload_file=upload_file, chunk_size=chunk_size):
        if first_chunk:
            if sorted(list(ol[0].keys())) != sorted(["key", "value"]):
                raise Exception("CSV format error: 'create' mode requires exactly 'key' and 'value' columns")
            first_chunk = False
        async with client_redis.pipeline(transaction=True) as pipe:
            for item in ol:
                val = orjson.dumps(item["value"]).decode("utf-8")
                if config_redis_cache_ttl_sec:
                    pipe.setex(item["key"], config_redis_cache_ttl_sec, val)
                else:
                    pipe.set(item["key"], val)
            await pipe.execute()
        count += len(ol)
    return count

async def func_redis_delete(*, upload_file: any, client_redis: any, chunk_size: int, func_api_file_to_chunks: any) -> int:
    """Batch delete objects in Redis from an uploaded CSV file."""
    count, first_chunk = 0, True
    async for ol in func_api_file_to_chunks(upload_file=upload_file, chunk_size=chunk_size):
        if first_chunk:
            if list(ol[0].keys()) != ["key"]:
                raise Exception("CSV format error: 'delete' mode requires exactly one 'key' column")
            first_chunk = False
        async with client_redis.pipeline(transaction=True) as pipe:
            for item in ol:
                pipe.delete(item["key"])
            await pipe.execute()
        count += len(ol)
    return count
