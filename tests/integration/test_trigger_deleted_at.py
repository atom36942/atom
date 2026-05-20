import pytest
import asyncpg
from testcontainers.postgres import PostgresContainer
from argon2 import PasswordHasher
from core.function import func_postgres_schema_init


@pytest.mark.asyncio
async def test_deleted_at_set_on_soft_delete():
    """When is_deleted changes from 0 to 1, deleted_at should be auto-set to NOW()."""
    with PostgresContainer("postgis/postgis:16-3.4-alpine") as postgres:
        pool = await asyncpg.create_pool(dsn=postgres.get_connection_url().replace("+psycopg2", ""))
        try:
            await func_postgres_schema_init(
                client_postgres_pool=pool,
                client_password_hasher=PasswordHasher(),
                config_postgres={
                    "table": {
                        "users": [
                            {"name": "created_at", "datatype": "timestamptz", "default": "now()"},
                            {"name": "is_active", "datatype": "smallint", "default": 1, "in": (0, 1)},
                            {"name": "is_deleted", "datatype": "smallint", "default": 0, "in": (0, 1)},
                            {"name": "deleted_at", "datatype": "timestamptz"},
                            {"name": "type", "datatype": "smallint", "is_mandatory": 1},
                            {"name": "username", "datatype": "text", "unique": "username,type"},
                            {"name": "password", "datatype": "text"},
                            {"name": "role", "datatype": "smallint"},
                        ]
                    },
                    "control": {"is_enable_users_set_deleted_at": 1},
                },
                config_root_user_password="password",
            )

            async with pool.acquire() as conn:
                # Insert a normal row
                row = await conn.fetchrow("INSERT INTO users (type, username, password) VALUES (1, 'testuser', 'pass') RETURNING *")
                uid = row["id"]
                assert row["is_deleted"] == 0
                assert row["deleted_at"] is None

                # Soft delete: is_deleted 0 → 1
                updated = await conn.fetchrow("UPDATE users SET is_deleted = 1 WHERE id = $1 RETURNING *", uid)
                assert updated["is_deleted"] == 1
                assert updated["deleted_at"] is not None
                print(f"\n✅ deleted_at set on soft delete: {updated['deleted_at']}")

        finally:
            await pool.close()


@pytest.mark.asyncio
async def test_deleted_at_cleared_on_reactivation():
    """When is_deleted changes from 1 to 0, deleted_at should be reset to NULL."""
    with PostgresContainer("postgis/postgis:16-3.4-alpine") as postgres:
        pool = await asyncpg.create_pool(dsn=postgres.get_connection_url().replace("+psycopg2", ""))
        try:
            await func_postgres_schema_init(
                client_postgres_pool=pool,
                client_password_hasher=PasswordHasher(),
                config_postgres={
                    "table": {
                        "users": [
                            {"name": "created_at", "datatype": "timestamptz", "default": "now()"},
                            {"name": "is_active", "datatype": "smallint", "default": 1, "in": (0, 1)},
                            {"name": "is_deleted", "datatype": "smallint", "default": 0, "in": (0, 1)},
                            {"name": "deleted_at", "datatype": "timestamptz"},
                            {"name": "type", "datatype": "smallint", "is_mandatory": 1},
                            {"name": "username", "datatype": "text", "unique": "username,type"},
                            {"name": "password", "datatype": "text"},
                            {"name": "role", "datatype": "smallint"},
                        ]
                    },
                    "control": {"is_enable_users_set_deleted_at": 1},
                },
                config_root_user_password="password",
            )

            async with pool.acquire() as conn:
                row = await conn.fetchrow("INSERT INTO users (type, username, password) VALUES (1, 'testuser2', 'pass') RETURNING *")
                uid = row["id"]

                # Soft delete first
                await conn.execute("UPDATE users SET is_deleted = 1 WHERE id = $1", uid)

                # Reactivate: is_deleted 1 → 0
                restored = await conn.fetchrow("UPDATE users SET is_deleted = 0 WHERE id = $1 RETURNING *", uid)
                assert restored["is_deleted"] == 0
                assert restored["deleted_at"] is None
                print("\n✅ deleted_at cleared on reactivation")

        finally:
            await pool.close()


@pytest.mark.asyncio
async def test_deleted_at_set_on_insert_with_is_deleted_1():
    """When a row is inserted with is_deleted=1, deleted_at should be auto-set."""
    with PostgresContainer("postgis/postgis:16-3.4-alpine") as postgres:
        pool = await asyncpg.create_pool(dsn=postgres.get_connection_url().replace("+psycopg2", ""))
        try:
            await func_postgres_schema_init(
                client_postgres_pool=pool,
                client_password_hasher=PasswordHasher(),
                config_postgres={
                    "table": {
                        "users": [
                            {"name": "created_at", "datatype": "timestamptz", "default": "now()"},
                            {"name": "is_active", "datatype": "smallint", "default": 1, "in": (0, 1)},
                            {"name": "is_deleted", "datatype": "smallint", "default": 0, "in": (0, 1)},
                            {"name": "deleted_at", "datatype": "timestamptz"},
                            {"name": "type", "datatype": "smallint", "is_mandatory": 1},
                            {"name": "username", "datatype": "text", "unique": "username,type"},
                            {"name": "password", "datatype": "text"},
                            {"name": "role", "datatype": "smallint"},
                        ]
                    },
                    "control": {"is_enable_users_set_deleted_at": 1},
                },
                config_root_user_password="password",
            )

            async with pool.acquire() as conn:
                row = await conn.fetchrow("INSERT INTO users (type, username, password, is_deleted) VALUES (1, 'testuser3', 'pass', 1) RETURNING *")
                assert row["is_deleted"] == 1
                assert row["deleted_at"] is not None
                print(f"\n✅ deleted_at set on insert with is_deleted=1: {row['deleted_at']}")

        finally:
            await pool.close()


@pytest.mark.asyncio
async def test_deleted_at_not_created_on_non_users_table():
    """The built-in deleted_at trigger is users-table specific."""
    with PostgresContainer("postgis/postgis:16-3.4-alpine") as postgres:
        pool = await asyncpg.create_pool(dsn=postgres.get_connection_url().replace("+psycopg2", ""))
        try:
            await func_postgres_schema_init(
                client_postgres_pool=pool,
                client_password_hasher=PasswordHasher(),
                config_postgres={
                    "table": {
                        "orders": [
                            {"name": "created_at", "datatype": "timestamptz", "default": "now()"},
                            {"name": "is_deleted", "datatype": "smallint", "default": 0, "in": (0, 1)},
                            {"name": "deleted_at", "datatype": "timestamptz"},
                            {"name": "title", "datatype": "text"},
                        ]
                    },
                    "control": {"is_enable_users_set_deleted_at": 1},
                },
                config_root_user_password="password",
            )

            async with pool.acquire() as conn:
                row = await conn.fetchrow("INSERT INTO orders (title) VALUES ('Order 1') RETURNING *")
                oid = row["id"]
                assert row["deleted_at"] is None

                # Soft delete: users-only trigger should not affect this table.
                updated = await conn.fetchrow("UPDATE orders SET is_deleted = 1 WHERE id = $1 RETURNING *", oid)
                assert updated["deleted_at"] is None

                # Reactivate
                restored = await conn.fetchrow("UPDATE orders SET is_deleted = 0 WHERE id = $1 RETURNING *", oid)
                assert restored["deleted_at"] is None
                print("\n✅ deleted_at trigger is not created on non-users table (orders)")

        finally:
            await pool.close()


@pytest.mark.asyncio
async def test_deleted_at_not_created_when_control_disabled():
    """When is_enable_users_set_deleted_at=0, the trigger should NOT be created."""
    with PostgresContainer("postgis/postgis:16-3.4-alpine") as postgres:
        pool = await asyncpg.create_pool(dsn=postgres.get_connection_url().replace("+psycopg2", ""))
        try:
            await func_postgres_schema_init(
                client_postgres_pool=pool,
                client_password_hasher=PasswordHasher(),
                config_postgres={
                    "table": {
                        "orders": [
                            {"name": "created_at", "datatype": "timestamptz", "default": "now()"},
                            {"name": "is_deleted", "datatype": "smallint", "default": 0, "in": (0, 1)},
                            {"name": "deleted_at", "datatype": "timestamptz"},
                            {"name": "title", "datatype": "text"},
                        ]
                    },
                    "control": {"is_enable_users_set_deleted_at": 0},
                },
                config_root_user_password="password",
            )

            async with pool.acquire() as conn:
                row = await conn.fetchrow("INSERT INTO orders (title) VALUES ('Order 1') RETURNING *")
                oid = row["id"]

                # Soft delete — deleted_at should remain NULL since trigger is disabled
                updated = await conn.fetchrow("UPDATE orders SET is_deleted = 1 WHERE id = $1 RETURNING *", oid)
                assert updated["deleted_at"] is None
                print("\n✅ deleted_at trigger correctly NOT created when control disabled")

        finally:
            await pool.close()


@pytest.mark.asyncio
async def test_deleted_at_null_to_1_transition_on_users():
    """When users.is_deleted changes from NULL to 1, deleted_at should be set."""
    with PostgresContainer("postgis/postgis:16-3.4-alpine") as postgres:
        pool = await asyncpg.create_pool(dsn=postgres.get_connection_url().replace("+psycopg2", ""))
        try:
            await func_postgres_schema_init(
                client_postgres_pool=pool,
                client_password_hasher=PasswordHasher(),
                config_postgres={
                    "table": {
                        "users": [
                            {"name": "is_deleted", "datatype": "smallint"},
                            {"name": "deleted_at", "datatype": "timestamptz"},
                            {"name": "type", "datatype": "smallint", "is_mandatory": 1},
                            {"name": "username", "datatype": "text", "unique": "username,type"},
                            {"name": "password", "datatype": "text"},
                            {"name": "role", "datatype": "smallint"},
                            {"name": "is_active", "datatype": "smallint"},
                        ]
                    },
                    "control": {"is_enable_users_set_deleted_at": 1},
                },
                config_root_user_password="password",
            )

            async with pool.acquire() as conn:
                # Insert with is_deleted = NULL (no default)
                row = await conn.fetchrow("INSERT INTO users (type, username, password) VALUES (1, 'nullable_user', 'pass') RETURNING *")
                iid = row["id"]
                assert row["is_deleted"] is None
                assert row["deleted_at"] is None

                # NULL → 1
                updated = await conn.fetchrow("UPDATE users SET is_deleted = 1 WHERE id = $1 RETURNING *", iid)
                assert updated["deleted_at"] is not None

                # 1 → NULL
                restored = await conn.fetchrow("UPDATE users SET is_deleted = NULL WHERE id = $1 RETURNING *", iid)
                assert restored["deleted_at"] is None
                print("\n✅ deleted_at handles NULL ↔ 1 transitions correctly")

        finally:
            await pool.close()
