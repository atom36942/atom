"""Database doubles: record calls without executing SQL or opening connections."""
from unittest.mock import AsyncMock, MagicMock


def database():
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchval = AsyncMock(return_value=0)
    conn.execute = AsyncMock(return_value="DELETE 0")
    transaction = MagicMock()
    transaction.__aexit__.return_value = False
    conn.transaction.return_value = transaction
    pool = MagicMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    pool.acquire.return_value.__aexit__.return_value = False
    return pool, conn
