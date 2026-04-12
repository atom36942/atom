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
