async def func_user_profile_read(*, client_postgres_pool: any, user_id: int, config_sql: dict, func_user_single_read: callable) -> dict:
    """Read full user profile and update last activity status."""
    import asyncio
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

async def func_user_account_delete(*, mode: str, client_postgres_pool: any, user_id: int) -> str:
    """Delete a user account either softly (flag) or hardly (row removal)."""
    async with client_postgres_pool.acquire() as conn:
        user = await conn.fetchrow("SELECT role FROM users WHERE id=$1", user_id)
        if not user:
            raise Exception("user not found")
        if user["role"] is not None:
            raise Exception("account with role cannot be deleted")
        if mode == "soft":
            query = "UPDATE users SET is_deleted=1 WHERE id=$1"
        elif mode == "hard":
            query = "DELETE FROM users WHERE id=$1"
        else:
            raise Exception(f"invalid delete mode: {mode}, allowed: soft, hard")
        await conn.execute(query, user_id)
    return "account deleted"

async def func_user_single_read(*, client_postgres_pool: any, user_id: int) -> dict:
    """Read a single user's full record by their ID."""
    async with client_postgres_pool.acquire() as conn:
        record = await conn.fetchrow("SELECT * FROM users WHERE id=$1;", user_id)
        if not record:
            raise Exception("user not found")
        return dict(record)

async def func_user_api_usage_read(*, client_postgres_pool: any, days: int, user_id: int) -> list:
    """Read API usage logs for a specific user within a day limit."""
    query = "SELECT api, count(*) FROM log_api WHERE created_at >= NOW() - ($1 * INTERVAL '1 day') AND created_by_id=$2 GROUP BY api LIMIT 1000;"
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, days, user_id)
        return [dict(r) for r in records]

async def func_message_inbox(*, client_postgres_pool: any, user_id: int, mode: str, order: str, limit: int, page: int) -> list:
    """Read a conversation-summarized inbox for a user with unread filtering."""
    where_clause = "user_id=$1 AND is_read=1" if mode == "read" else "user_id=$1 AND is_read IS DISTINCT FROM 1" if mode == "unread" else "1=1"
    query = f"WITH chat_summary AS (SELECT id, ABS(created_by_id - user_id) AS conversation_id FROM message WHERE (created_by_id=$1 OR user_id=$1)), latest_messages AS (SELECT MAX(id) AS id FROM chat_summary GROUP BY conversation_id), inbox_data AS (SELECT m.* FROM latest_messages LEFT JOIN message AS m ON latest_messages.id=m.id) SELECT * FROM inbox_data WHERE {where_clause} ORDER BY {order} LIMIT {limit} OFFSET {(page-1)*limit};"
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, user_id)
        return [dict(r) for r in records]

async def func_message_received(*, client_postgres_pool: any, user_id: int, mode: str, order: str, limit: int, page: int) -> list:
    """Read all messages received by a specific user and optionally mark unread ones as read (identifier validated)."""
    import asyncio
    unread_filter = "AND is_read=1" if mode == "read" else "AND is_read IS DISTINCT FROM 1" if mode == "unread" else ""
    query = f"SELECT * FROM message WHERE user_id=$1 {unread_filter} ORDER BY {order} LIMIT {limit} OFFSET {(page-1)*limit};"
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, user_id)
        obj_list = [dict(r) for r in records]
        if obj_list:
            mark_read_ids = [r["id"] for r in obj_list if r.get("is_read") != 1]
            if mark_read_ids:
                async def _mark_read():
                    async with client_postgres_pool.acquire() as conn:
                        await conn.execute(f"UPDATE message SET is_read=1 WHERE id IN ({','.join(map(str, mark_read_ids))})")
                asyncio.create_task(_mark_read())
    return obj_list

async def func_message_thread(*, client_postgres_pool: any, user_one_id: int, user_id: int, order: str, limit: int, page: int) -> list:
    """Read the full message thread between two users."""
    query = f"SELECT * FROM message WHERE ((created_by_id=$1 AND user_id=$2) OR (created_by_id=$2 AND user_id=$1)) ORDER BY {order} LIMIT {limit} OFFSET {(page-1)*limit};"
    async with client_postgres_pool.acquire() as conn:
        records = await conn.fetch(query, user_one_id, user_id)
        return [dict(r) for r in records]

async def func_message_thread_mark_read(*, client_postgres_pool: any, current_user_id: int, partner_id: int) -> None:
    """Mark all messages in a thread as read for the current user."""
    async with client_postgres_pool.acquire() as conn:
        await conn.execute("UPDATE message SET is_read=1 WHERE created_by_id=$1 AND user_id=$2;", partner_id, current_user_id)
    return None

async def func_message_delete_single(*, client_postgres_pool: any, id: int, user_id: int) -> str:
    """Delete a single message given its ID and user context."""
    async with client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM message WHERE id=$1 AND (created_by_id=$2 OR user_id=$2)", id, user_id)
    return "message deleted"

async def func_message_delete_bulk(*, client_postgres_pool: any, user_id: int, mode: str) -> str:
    """Delete multiple messages for a user based on context (sent, received, all)."""
    if mode == "sent":
        query = "DELETE FROM message WHERE created_by_id=$1"
        args = (user_id,)
    elif mode == "received":
        query = "DELETE FROM message WHERE user_id=$1"
        args = (user_id,)
    elif mode == "all":
        query = "DELETE FROM message WHERE (created_by_id=$1 OR user_id=$1)"
        args = (user_id,)
    else:
        raise Exception(f"invalid delete mode: {mode}, allowed: sent, received, all")
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(query, *args)
    return "messages deleted"
