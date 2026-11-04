"""Shared test helpers: database doubles that record calls without executing SQL, and the settings that turn on tests against real services."""
import os
from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from dotenv import dotenv_values


def service_setting(name):
    """An ATOM_TEST_* setting: from the environment (CI), else from the project's .env, so local runs need no prefix. Only that key is read: the rest of .env never reaches the tests."""
    return os.environ.get(name) or dotenv_values(Path(__file__).resolve().parents[1] / ".env").get(name)


def database():
    conn = MagicMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchval = AsyncMock(return_value=0)
    conn.execute = AsyncMock(return_value="DELETE 0")
    conn.is_in_transaction = MagicMock(return_value=False)
    transaction = MagicMock()
    transaction.__aexit__.return_value = False
    conn.transaction.return_value = transaction
    pool = MagicMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    pool.acquire.return_value.__aexit__.return_value = False
    return pool, conn
