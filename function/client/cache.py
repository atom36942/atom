async def func_client_read_redis(*, config_redis_url: str) -> any:
    """Initialize Redis client using connection pooling."""
    import redis.asyncio as redis
    return redis.Redis.from_pool(redis.ConnectionPool.from_url(config_redis_url))

async def func_client_read_redis_consumer(*, client_redis: any, channel_name: str) -> any:
    """Initialize Redis PubSub consumer and subscribe to a channel."""
    pubsub = client_redis.pubsub()
    await pubsub.subscribe(channel_name)
    return pubsub
