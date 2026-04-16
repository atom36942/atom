async def func_user_profile_read(*, client_postgres_pool: any, user_id: int, config_sql: dict) -> dict:
    """Read full user profile and update last activity status."""
    import asyncio
    # Import locally to avoid circular dependency if user/read.py is processed later
    from .read import func_user_single_read
    user = await func_user_single_read(client_postgres_pool=client_postgres_pool, user_id=user_id)
    metadata = {}
    queries_metadata = config_sql.get("profile_metadata")
    if queries_metadata:
        async with client_postgres_pool.acquire() as conn:
            for key, sql_query in queries_metadata.items():
                records = await conn.fetch(sql_query, user_id)
                metadata[key] = [dict(record) for record in records]
    asyncio.create_task(client_postgres_pool.execute("UPDATE users SET last_active_at=NOW() WHERE id=$1", user_id))
    return {**user, **metadata}
