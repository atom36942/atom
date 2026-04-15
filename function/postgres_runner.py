async def func_postgres_runner(*, client_postgres_pool: any, mode: str, query: str) -> any:
    """Execute raw SQL queries in 'read' or 'write' mode with basic DDL and DELETE protection."""
    import re
    if mode != "read" and mode != "write":
        raise Exception(f"invalid mode: {mode}")
    ql = query.lower().strip()
    if re.search(r"\bdrop\b", ql):
        raise Exception("keyword drop forbidden")
    if re.search(r"\btruncate\b", ql):
        raise Exception("keyword truncate forbidden")
    if re.search(r"\bdelete\b", ql):
        raise Exception("keyword delete forbidden")
    if mode == "read" and not ql.startswith(("select", "with", "explain", "show", "describe")):
        raise Exception("read mode restricted to select/with/explain/show/describe")
    async with client_postgres_pool.acquire() as conn:
        if "returning" in ql:
            return await conn.fetch(query, timeout=15)
        return await conn.execute(query, timeout=15)
        
async def func_postgres_export(*, client_postgres_pool: any, query: str) -> any:
    """Stream PostgreSQL query results as a CSV Iterative Response with DDL and DELETE protection."""
    import re
    from fastapi.responses import StreamingResponse
    ql = query.lower().strip()
    if re.search(r"\bdrop\b", ql):
        raise Exception("keyword drop forbidden")
    if re.search(r"\btruncate\b", ql):
        raise Exception("keyword truncate forbidden")
    if re.search(r"\bdelete\b", ql):
        raise Exception("keyword delete forbidden")
    if not ql.startswith(("select", "with", "explain", "show", "describe")):
        raise Exception("export restricted to select/with/explain/show/describe")
    async def generate():
        async with client_postgres_pool.acquire() as conn:
            async with conn.transaction():
                is_first = 1
                async for record in conn.cursor(query):
                    if is_first == 1:
                        yield ",".join(record.keys()) + "\n"
                        is_first = 0
                    yield ",".join([f"\"{str(v).replace(chr(34), chr(34)*2)}\"" if v is not None else "" for v in record.values()]) + "\n"
    return StreamingResponse(generate(), media_type="text/csv")