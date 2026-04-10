async def func_user_single_read(client_postgres_pool: any, user_id: int) -> dict:
    """Read a single user's record by ID."""
    async with client_postgres_pool.acquire() as conn:
        record = await conn.fetchrow("SELECT * FROM users WHERE id = $1;", user_id)
    return dict(record) if record else {}

async def func_my_profile_read(client_postgres_pool: any, user_id: int, config_sql_profile_metadata: dict) -> dict:
    """Read full profile data for the current user, including dynamic metadata aggregates defined in SQL config."""
    async with client_postgres_pool.acquire() as conn:
        user_record = await conn.fetchrow("SELECT * FROM users WHERE id = $1;", user_id)
        if not user_record:
            return {}
        profile = dict(user_record)
        if config_sql_profile_metadata:
            for key, sql in config_sql_profile_metadata.items():
                try:
                    res = await conn.fetchrow(sql, user_id)
                    profile[key] = res[0] if res else 0
                except Exception:
                    profile[key] = 0
        return profile
