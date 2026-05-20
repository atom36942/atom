import copy

import asyncpg
import pytest
from argon2 import PasswordHasher
from testcontainers.postgres import PostgresContainer

from core import config
from core.function import func_postgres_schema_init


async def fetch_control_checks(conn):
    rows = await conn.fetch(
        """
        SELECT *
        FROM (
          VALUES
            ('is_enable_extension_postgis', EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis')),
            ('is_enable_extension_pg_trgm', EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm')),
            ('is_enable_extension_btree_gin', EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'btree_gin')),
            ('is_disable_drop_schema_or_table', EXISTS (SELECT 1 FROM pg_event_trigger WHERE evtname = 'trigger_drop_disable')),
            ('is_disable_drop_column', EXISTS (SELECT 1 FROM pg_event_trigger WHERE evtname = 'trigger_drop_column_disable')),
            ('is_disable_truncate_users', EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid WHERE c.relname = 'users' AND t.tgname = 'trigger_truncate_disable_users' AND NOT t.tgisinternal)),
            ('is_disable_users_delete_role', EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_proc p ON p.oid = t.tgfoid WHERE c.relname = 'users' AND t.tgname = 'trigger_delete_disable_role_users' AND p.proname = 'func_delete_disable_role_users' AND NOT t.tgisinternal)),
            ('is_enable_users_protect_root', EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_proc p ON p.oid = t.tgfoid WHERE c.relname = 'users' AND t.tgname = 'trigger_protect_root_users' AND p.proname = 'func_protect_root_users' AND NOT t.tgisinternal)),
            ('is_enable_users_root_upsert', EXISTS (SELECT 1 FROM users WHERE id = 1 AND type = 1 AND username = 'atom' AND role = 1 AND is_active = 1)),
            ('is_enable_users_password_log', EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_proc p ON p.oid = t.tgfoid WHERE c.relname = 'users' AND t.tgname = 'trigger_password_log_users' AND p.proname = 'func_password_log_users' AND NOT t.tgisinternal)),

            ('table_delete_disable_row_users', EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid WHERE c.relname = 'users' AND t.tgname = 'trigger_delete_disable_users' AND NOT t.tgisinternal)),
            ('table_delete_disable_row_bulk_users', EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid WHERE c.relname = 'users' AND t.tgname = 'trigger_delete_disable_bulk_users' AND NOT t.tgisinternal)),
            ('is_enable_autovacuum_optimize_users', EXISTS (SELECT 1 FROM pg_class WHERE relname = 'users' AND reloptions @> ARRAY['autovacuum_vacuum_scale_factor=0.05', 'autovacuum_analyze_scale_factor=0.02'])),
            ('is_enable_users_set_deleted_at', EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_proc p ON p.oid = t.tgfoid WHERE c.relname = 'users' AND t.tgname = 'trigger_set_deleted_at_users' AND p.proname = 'func_set_deleted_at_users' AND NOT t.tgisinternal)),
            ('is_enable_delete_disable_is_protected', EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_attribute a ON a.attrelid = c.oid JOIN pg_proc p ON p.oid = t.tgfoid WHERE t.tgname = 'trigger_delete_disable_is_protected_' || c.relname AND a.attname = 'is_protected' AND NOT a.attisdropped AND p.proname = 'func_delete_disable_is_protected' AND NOT t.tgisinternal)),
            ('is_enable_updated_at_set', EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_attribute a ON a.attrelid = c.oid JOIN pg_proc p ON p.oid = t.tgfoid WHERE t.tgname = 'trigger_updated_at_set_' || c.relname AND a.attname = 'updated_at' AND NOT a.attisdropped AND p.proname = 'func_set_updated_at' AND NOT t.tgisinternal))
        ) AS checks(control_key, is_created)
        """
    )
    return {row["control_key"]: row["is_created"] for row in rows}


def minimal_control_config(control):
    return {
        "table": {
            "users": [
                {"name": "type", "datatype": "smallint", "is_mandatory": 1},
                {"name": "username", "datatype": "text", "unique": "username,type"},
                {"name": "password", "datatype": "text"},
                {"name": "role", "datatype": "smallint"},
                {"name": "is_active", "datatype": "smallint"},
                {"name": "is_deleted", "datatype": "smallint", "default": 0},
                {"name": "deleted_at", "datatype": "timestamptz"},
                {"name": "updated_at", "datatype": "timestamptz"},
                {"name": "is_protected", "datatype": "smallint", "default": 0},
            ],
            "log_users_password": [
                {"name": "user_id", "datatype": "bigint"},
                {"name": "password", "datatype": "text"},
            ],
            "demo_control": [
                {"name": "user_id", "datatype": "bigint"},
                {"name": "created_by_id", "datatype": "bigint"},
                {"name": "is_deleted", "datatype": "smallint", "default": 0},
                {"name": "is_protected", "datatype": "smallint", "default": 0},
                {"name": "updated_at", "datatype": "timestamptz"},
                {"name": "title", "datatype": "text"},
            ],
        },
        "control": control,
    }


@pytest.mark.asyncio
async def test_config_postgres_control_catalog_matches_core_config_defaults():
    with PostgresContainer("postgis/postgis:16-3.4-alpine") as postgres:
        pool = await asyncpg.create_pool(dsn=postgres.get_connection_url().replace("+psycopg2", ""))
        try:
            await func_postgres_schema_init(
                client_postgres_pool=pool,
                client_password_hasher=PasswordHasher(),
                config_postgres=copy.deepcopy(config.config_postgres),
                config_root_user_password=config.config_root_user_password,
            )

            async with pool.acquire() as conn:
                checks = await fetch_control_checks(conn)

            assert checks == {
                "is_enable_extension_postgis": True,
                "is_enable_extension_pg_trgm": True,
                "is_enable_extension_btree_gin": True,
                "is_disable_drop_schema_or_table": False,
                "is_disable_drop_column": False,
                "is_disable_truncate_users": False,
                "is_disable_users_delete_role": True,
                "is_enable_users_protect_root": True,
                "is_enable_users_root_upsert": True,
                "is_enable_users_password_log": True,

                "table_delete_disable_row_users": True,
                "table_delete_disable_row_bulk_users": True,
                "is_enable_autovacuum_optimize_users": True,
                "is_enable_users_set_deleted_at": True,
                "is_enable_delete_disable_is_protected": True,
                "is_enable_updated_at_set": True,
            }
        finally:
            await pool.close()


@pytest.mark.asyncio
async def test_postgres_schema_init_control_triggers_enforce_runtime_behavior():
    with PostgresContainer("postgis/postgis:16-3.4-alpine") as postgres:
        pool = await asyncpg.create_pool(dsn=postgres.get_connection_url().replace("+psycopg2", ""))
        try:
            await func_postgres_schema_init(
                client_postgres_pool=pool,
                client_password_hasher=PasswordHasher(),
                config_postgres=minimal_control_config(
                    {
                        "is_enable_users_protect_root": 1,
                        "is_enable_users_root_upsert": 1,
                        "is_enable_users_password_log": 1,

                        "is_disable_users_delete_role": 0,
                        "is_enable_users_set_deleted_at": 1,
                        "is_enable_delete_disable_is_protected": 1,
                        "is_enable_updated_at_set": 1,
                    }
                ),
                config_root_user_password="root-password",
            )

            async with pool.acquire() as conn:
                root = await conn.fetchrow("SELECT id, username, role, is_active FROM users WHERE id = 1")
                assert dict(root) == {"id": 1, "username": "atom", "role": 1, "is_active": 1}

                with pytest.raises(asyncpg.PostgresError, match="DELETE not allowed for root user"):
                    await conn.execute("DELETE FROM users WHERE id = 1")

                with pytest.raises(asyncpg.PostgresError, match="Updates to type, username, role, or is_active"):
                    await conn.execute("UPDATE users SET role = 2 WHERE id = 1")

                await conn.execute("UPDATE users SET password = 'changed-password' WHERE id = 1")
                password_log_count = await conn.fetchval("SELECT COUNT(*) FROM log_users_password WHERE user_id = 1")
                assert password_log_count == 1

                deleted_root = await conn.fetchrow("UPDATE users SET is_deleted = 1 WHERE id = 1 RETURNING deleted_at")
                assert deleted_root["deleted_at"] is not None

                row = await conn.fetchrow("INSERT INTO demo_control (title, is_protected) VALUES ('protected', 1) RETURNING id")
                with pytest.raises(asyncpg.PostgresError, match="DELETE not allowed for protected row"):
                    await conn.execute("DELETE FROM demo_control WHERE id = $1", row["id"])

                before = await conn.fetchrow("INSERT INTO demo_control (title) VALUES ('timestamps') RETURNING id, updated_at")
                assert before["updated_at"] is None
                after = await conn.fetchrow("UPDATE demo_control SET title = 'timestamps changed' WHERE id = $1 RETURNING updated_at", before["id"])
                assert after["updated_at"] is not None


        finally:
            await pool.close()


@pytest.mark.asyncio
async def test_new_automatic_logic_control_switches_remove_managed_triggers_when_disabled():
    with PostgresContainer("postgis/postgis:16-3.4-alpine") as postgres:
        pool = await asyncpg.create_pool(dsn=postgres.get_connection_url().replace("+psycopg2", ""))
        try:
            enabled_control = {
                "is_enable_users_protect_root": 1,
                "is_enable_users_root_upsert": 1,
                "is_enable_users_password_log": 1,
                "is_enable_delete_disable_is_protected": 1,
                "is_enable_updated_at_set": 1,
            }
            disabled_control = {
                "is_enable_users_protect_root": 0,
                "is_enable_users_root_upsert": 0,
                "is_enable_users_password_log": 0,
                "is_enable_delete_disable_is_protected": 0,
                "is_enable_updated_at_set": 0,
            }

            await func_postgres_schema_init(
                client_postgres_pool=pool,
                client_password_hasher=PasswordHasher(),
                config_postgres=minimal_control_config(enabled_control),
                config_root_user_password="root-password",
            )
            await func_postgres_schema_init(
                client_postgres_pool=pool,
                client_password_hasher=PasswordHasher(),
                config_postgres=minimal_control_config(disabled_control),
                config_root_user_password="root-password",
            )

            async with pool.acquire() as conn:
                trigger_names = set(
                    await conn.fetchval(
                        """
                        SELECT array_agg(t.tgname)
                        FROM pg_trigger t
                        JOIN pg_class c ON c.oid = t.tgrelid
                        WHERE c.relname IN ('users', 'demo_control')
                          AND t.tgname LIKE 'trigger_%'
                          AND NOT t.tgisinternal
                        """
                    )
                    or []
                )

                assert "trigger_protect_root_users" not in trigger_names
                assert "trigger_password_log_users" not in trigger_names
                assert "trigger_delete_disable_is_protected_users" not in trigger_names
                assert "trigger_delete_disable_is_protected_demo_control" not in trigger_names
                assert "trigger_updated_at_set_users" not in trigger_names
                assert "trigger_updated_at_set_demo_control" not in trigger_names

                await conn.execute("UPDATE users SET role = 2 WHERE id = 1")
                await conn.execute("DELETE FROM users WHERE id = 1")
                assert await conn.fetchval("SELECT COUNT(*) FROM users WHERE id = 1") == 0
        finally:
            await pool.close()
