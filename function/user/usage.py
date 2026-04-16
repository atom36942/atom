async def func_user_api_usage_read(*, client_postgres_pool: any, days: int, user_id: int) -> list:
    """Read API usage logs for a specific user within a day limit."""
    query = "SELECT api, count(*) FROM log_api WHERE created_at >= NOW() - ($1 * INTERVAL '1 day') AND created_by_id=$2 GROUP BY api LIMIT 1000;"
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, days, user_id)
        return [dict(r) for r in records]
