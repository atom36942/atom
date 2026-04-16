async def func_client_read_postgres(*, config_postgres: dict) -> any:
    """Initialize PostgreSQL connection pool."""
    import asyncpg
    return await asyncpg.create_pool(dsn=config_postgres["dsn"], min_size=config_postgres["min_size"], max_size=config_postgres["max_size"])

async def func_client_read_mongodb(*, config_mongodb_url: str) -> any:
    """Initialize MongoDB client."""
    import motor.motor_asyncio
    return motor.motor_asyncio.AsyncIOMotorClient(config_mongodb_url)
