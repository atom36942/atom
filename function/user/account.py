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
