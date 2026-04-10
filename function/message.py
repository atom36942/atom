async def func_message_inbox(client_postgres_pool: any, user_id: int, limit_count: int = None, page_number: int = None) -> list:
    """Read a user's inbox, grouping messages by the other participant (sender or receiver) and showing only the latest message per thread."""
    limit = min(max(int(limit_count or 100), 1), 500)
    page = max(int(page_number or 1), 1)
    query = f"WITH x AS (SELECT DISTINCT ON (LEAST(created_by_id, user_id), GREATEST(created_by_id, user_id)) * FROM message WHERE created_by_id=$1 OR user_id=$1 ORDER BY LEAST(created_by_id, user_id), GREATEST(created_by_id, user_id), created_at DESC) SELECT x.*, u.name AS contact_name FROM x LEFT JOIN users u ON u.id = CASE WHEN x.created_by_id=$1 THEN x.user_id ELSE x.created_by_id END ORDER BY created_at DESC LIMIT {limit} OFFSET {(page-1)*limit};"
    async with client_postgres_pool.acquire() as conn:
        return [dict(r) for r in (await conn.fetch(query, user_id))]

async def func_message_received(client_postgres_pool: any, user_id: int, limit_count: int = None, page_number: int = None) -> list:
    """Read all messages received by the current user with sender names."""
    limit = min(max(int(limit_count or 100), 1), 500)
    page = max(int(page_number or 1), 1)
    query = f"SELECT m.*, u.name AS sender_name FROM message m LEFT JOIN users u ON m.created_by_id=u.id WHERE m.user_id=$1 ORDER BY m.created_at DESC LIMIT {limit} OFFSET {(page-1)*limit};"
    async with client_postgres_pool.acquire() as conn:
        return [dict(r) for r in (await conn.fetch(query, user_id))]

async def func_message_thread(client_postgres_pool: any, user_id: int, contact_id: int, limit_count: int = None, page_number: int = None) -> list:
    """Read the full message exchange history between two specific users."""
    limit = min(max(int(limit_count or 100), 1), 500)
    page = max(int(page_number or 1), 1)
    query = f"SELECT m.*, u.name AS sender_name FROM message m LEFT JOIN users u ON m.created_by_id=u.id WHERE (m.created_by_id=$1 AND m.user_id=$2) OR (m.created_by_id=$2 AND m.user_id=$1) ORDER BY m.created_at DESC LIMIT {limit} OFFSET {(page-1)*limit};"
    async with client_postgres_pool.acquire() as conn:
        return [dict(r) for r in (await conn.fetch(query, user_id, contact_id))]

async def func_message_thread_mark_read(client_postgres_pool: any, user_id: int, contact_id: int) -> str:
    """Mark all messages in a specific thread as read for the receiver."""
    query = "UPDATE message SET is_read=1 WHERE user_id=$1 AND created_by_id=$2 AND is_read=0;"
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(query, user_id, contact_id)
    return "thread marked read"

async def func_message_delete_single(client_postgres_pool: any, user_id: int, message_id: int) -> str:
    """Delete a single message record ensuring the user is a participant in that message."""
    query = "DELETE FROM message WHERE id = $1 AND (created_by_id = $2 OR user_id = $2);"
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(query, message_id, user_id)
    return "message deleted"

async def func_message_delete_bulk(client_postgres_pool: any, user_id: int, contact_id: int) -> str:
    """Delete all messages in a specific thread history for both participants."""
    query = "DELETE FROM message WHERE (created_by_id=$1 AND user_id=$2) OR (created_by_id=$2 AND user_id=$1);"
    async with client_postgres_pool.acquire() as conn:
        await conn.execute(query, user_id, contact_id)
    return "thread deleted"
