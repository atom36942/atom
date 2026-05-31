import asyncpg
import pytest
from argon2 import PasswordHasher
from testcontainers.postgres import PostgresContainer

from core.function import func_postgres_schema_init
from core.script.worker_users_delete import execute
from unittest.mock import patch
import asyncio


def worker_test_config():
    return {
        "table": {
            "users": [
                {"name": "id", "datatype": "bigserial", "is_primary": 1},
                {"name": "type", "datatype": "smallint"},
                {"name": "username", "datatype": "text"},
                {"name": "password", "datatype": "text"},
                {"name": "deleted_at", "datatype": "timestamptz"},
            ],
            "log_users_delete": [
                {"name": "id", "datatype": "bigserial", "is_primary": 1},
                {"name": "created_at", "datatype": "timestamptz", "default": "now()"},
                {"name": "updated_at", "datatype": "timestamptz"},
                {"name": "user_id", "datatype": "bigint", "is_mandatory": 1},
                {"name": "event", "datatype": "smallint", "is_mandatory": 1},
                {"name": "status", "datatype": "smallint", "default": 1},
                {"name": "worker_status", "datatype": "smallint", "default": 1},
                {"name": "worker_retry_count", "datatype": "integer", "default": 0},
                {"name": "worker_next_retry_at", "datatype": "timestamptz", "default": "now()"},
                {"name": "worker_processed_at", "datatype": "timestamptz"},
                {"name": "worker_last_error", "datatype": "text"},
            ],
            "owned_doc": [
                {"name": "id", "datatype": "bigserial", "is_primary": 1},
                {"name": "created_at", "datatype": "timestamptz", "default": "now()"},
                {"name": "created_by_id", "datatype": "bigint"},
                {"name": "user_id", "datatype": "bigint"},
                {"name": "deleted_at", "datatype": "timestamptz"},
                {"name": "is_protected", "datatype": "boolean"},
                {"name": "title", "datatype": "text"},
            ],
        },
        "control": {
            "is_enable_delete_disable_users_root": 0,
            "is_enable_users_root_upsert": 0,
            "is_enable_log_users_password": 0,
            "is_enable_delete_disable_users_role": 0,
            "is_enable_delete_disable_users_role_soft": 0,
        },
    }


@pytest.mark.asyncio
async def test_users_delete_worker_processes_events_and_retention():
    with PostgresContainer("postgis/postgis:16-3.4-alpine") as postgres:
        db_url = postgres.get_connection_url().replace("+psycopg2", "")
        pool = await asyncpg.create_pool(dsn=db_url)
        try:
            await func_postgres_schema_init(
                client_postgres_pool=pool,
                client_password_hasher=PasswordHasher(),
                config_postgres=worker_test_config(),
                config_root_user_password="root-password",
            )

            async def run_worker_once():
                with patch("core.script.worker_users_delete.config_postgres_url", db_url):
                    with patch("asyncio.sleep", side_effect=asyncio.CancelledError):
                        try:
                            await execute()
                        except asyncio.CancelledError:
                            pass

            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO owned_doc (created_by_id, user_id, is_protected, title)
                    VALUES
                      (10, NULL, false, 'created owner'),
                      (NULL, 10, false, 'user owner'),
                      (10, 10, true, 'protected owner'),
                      (11, 11, false, 'other owner')
                    """
                )
                await conn.execute("INSERT INTO log_users_delete (user_id, event, worker_status) VALUES (10, 1, 1)")

            await run_worker_once()

            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT title, deleted_at FROM owned_doc ORDER BY id")
                assert rows[0]["deleted_at"] is not None
                assert rows[1]["deleted_at"] is not None
                assert rows[2]["deleted_at"] is None
                assert rows[3]["deleted_at"] is None
                assert await conn.fetchval("SELECT worker_status FROM log_users_delete WHERE event = 1") == 3

                await conn.execute("INSERT INTO log_users_delete (user_id, event, worker_status) VALUES (10, 2, 1)")

            await run_worker_once()

            async with pool.acquire() as conn:
                restored = await conn.fetch(
                    "SELECT COUNT(*) FROM owned_doc WHERE title IN ('created owner', 'user owner') AND deleted_at IS NULL"
                )
                assert restored[0]["count"] == 2
                assert await conn.fetchval("SELECT worker_status FROM log_users_delete WHERE event = 2") == 3

                await conn.execute(
                    """
                    INSERT INTO owned_doc (created_by_id, deleted_at, is_protected, title)
                    VALUES
                      (10, NOW() - INTERVAL '31 days', false, 'old deleted'),
                      (10, NOW() - INTERVAL '31 days', true, 'old protected')
                    """
                )

            await run_worker_once()

            async with pool.acquire() as conn:
                assert await conn.fetchval("SELECT COUNT(*) FROM owned_doc WHERE title = 'old deleted'") == 0
                assert await conn.fetchval("SELECT COUNT(*) FROM owned_doc WHERE title = 'old protected'") == 1
        finally:
            await pool.close()
