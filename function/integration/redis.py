async def func_redis_object_create(*, client_redis: any, keys: list, objects: list, config_redis_cache_ttl_sec: int) -> None:
    """Batch create/update objects in Redis with optional expiration in a pipeline transaction."""
    import orjson
    async with client_redis.pipeline(transaction=True) as pipe:
        for key, obj in zip(keys, objects):
            val = orjson.dumps(obj).decode("utf-8")
            if config_redis_cache_ttl_sec:
                pipe.setex(key, config_redis_cache_ttl_sec, val)
            else:
                pipe.set(key, val)
        await pipe.execute()
    return None

async def func_redis_object_delete(*, client_redis: any, keys: list) -> None:
    """Batch delete objects in Redis using a pipeline transaction."""
    async with client_redis.pipeline(transaction=True) as pipe:
        for key in keys:
            pipe.delete(key)
        await pipe.execute()
    return None
