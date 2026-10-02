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


APP_TEST_ENV = {
    "config_token_secret_key": "atom-http-test-secret-key-at-least-32-bytes",
    "config_root_user_password": "root-test-password",
    "config_signup_allowed_roles": "[5]",
    "config_postgres_buffer_flush_auto_sec": "1",
}


def app_start(*, env):
    """Boot the real app (lifespan included) from a temp working directory with only APP_TEST_ENV + env.

    config.py loads .env from the working directory and startup resets ./tmp, so running
    from the repo root would read developer secrets and wipe tmp/. Returns a handle for app_stop.
    """
    import io
    import sys
    import tempfile
    from contextlib import redirect_stderr
    from unittest.mock import patch
    handle = {"workdir": tempfile.TemporaryDirectory(), "previous_cwd": os.getcwd()}
    os.chdir(handle["workdir"].name)
    handle["env"] = patch.dict(os.environ, {**APP_TEST_ENV, **env})
    handle["env"].start()
    for key in [k for k in os.environ if k.lower().startswith("config_") and k not in APP_TEST_ENV and k not in env]:
        del os.environ[key]
    # The app prints a traceback for every handled error; these tests trigger 4xx on purpose.
    handle["stderr"] = io.StringIO()
    handle["quiet"] = redirect_stderr(handle["stderr"])
    handle["quiet"].__enter__()
    sys.path.insert(0, str(REPO_ROOT))
    for module in ("main", "config", "config_extend"): sys.modules.pop(module, None)
    import main
    from fastapi.testclient import TestClient
    handle["app"], handle["client"] = main.app, TestClient(main.app)
    handle["client"].__enter__()
    return handle


def app_stop(handle):
    import sys
    try:
        handle["client"].__exit__(None, None, None)
    finally:
        handle["quiet"].__exit__(None, None, None)
        os.chdir(handle["previous_cwd"])
        handle["env"].stop()
        sys.path.remove(str(REPO_ROOT))
        for module in ("main", "config", "config_extend"): sys.modules.pop(module, None)
        handle["workdir"].cleanup()


def app_login(client, *, path, body):
    response = client.post(path, json=body)
    assert response.status_code == 200, response.text
    return response.json()["message"]["access_token"]
