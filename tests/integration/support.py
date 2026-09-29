"""Throwaway PostgreSQL databases for integration tests.

Set ATOM_TEST_POSTGRES_URL to a server where the user may CREATE DATABASE and
install extensions (postgis, pg_trgm, btree_gin). Each test class gets its own
database, dropped afterwards. Atom's schema blocks TRUNCATE and user deletes, so
tests get isolation by cloning a schema-initialised template database instead of
cleaning tables. Without the variable these tests are skipped.
"""
import ast
import asyncio
import os
import secrets
import unittest
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg

ADMIN_URL = os.environ.get("ATOM_TEST_POSTGRES_URL")
REPO_ROOT = Path(__file__).resolve().parents[2]
requires_postgres = unittest.skipUnless(ADMIN_URL, "set ATOM_TEST_POSTGRES_URL to run PostgreSQL integration tests")


def config_postgres():
    """Read the schema literal from config.py without importing it (importing would load .env)."""
    tree = ast.parse((REPO_ROOT / "config.py").read_text())
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "config_postgres")
    return ast.literal_eval(node.value)


def database_url(name):
    parts = urlsplit(ADMIN_URL)
    return urlunsplit((parts.scheme, parts.netloc, f"/{name}", parts.query, parts.fragment))


def create_database(template=None):
    name = f"atom_test_{secrets.token_hex(4)}"
    async def run():
        conn = await asyncpg.connect(ADMIN_URL)
        try: await conn.execute(f'CREATE DATABASE "{name}"' + (f' TEMPLATE "{template}"' if template else ""))
        finally: await conn.close()
    asyncio.run(run())
    return name, database_url(name)


def drop_database(name):
    async def run():
        conn = await asyncpg.connect(ADMIN_URL)
        try: await conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        finally: await conn.close()
    asyncio.run(run())


def fetch(url, sql, *args):
    """Run one query on a fresh connection; usable from sync code and other event loops."""
    async def run():
        conn = await asyncpg.connect(url)
        try: return [dict(r) for r in await conn.fetch(sql, *args)]
        finally: await conn.close()
    return asyncio.run(run())
