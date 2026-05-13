import pytest
import asyncio
from testcontainers.postgres import PostgresContainer
import asyncpg
from core.function import func_postgres_schema_init, func_postgres_create, func_postgres_read, func_postgres_serialize

@pytest.mark.asyncio
async def test_postgres_integration_lifecycle():
    # 1. Start a real Postgres container
    with PostgresContainer("postgis/postgis:16-3.4-alpine") as postgres:
        conn_url = postgres.get_connection_url().replace("+psycopg2", "")
        
        # 2. Create a connection pool
        pool = await asyncpg.create_pool(dsn=conn_url)
        
        try:
            # 3. Initialize the schema
            config_postgres = {
                "extension": ["uuid-ossp"],
                "table": {
                    "test_integration": [
                        {"name": "title", "datatype": "text", "is_mandatory": 1},
                        {"name": "status", "datatype": "smallint", "default": 1}
                    ]
                },
                "control": {"is_enable_extension": 1}
            }
            
            from argon2 import PasswordHasher
            hasher = PasswordHasher()

            await func_postgres_schema_init(
                client_postgres_pool=pool,
                client_password_hasher=hasher,
                config_postgres=config_postgres,
                config_root_user_password="password"
            )
            
            # Fetch the schema so that serialization knows the types
            from core.function import func_postgres_schema_read
            schema_cache = await func_postgres_schema_read(client_postgres_pool=pool)
            
            # 4. Perform a real CREATE
            # NOTE: Payloads must be a list of dictionaries
            created_ids = await func_postgres_create(
                client_postgres_pool=pool,
                client_postgres_conn=None,
                client_password_hasher=hasher,
                func_postgres_serialize=func_postgres_serialize, # Pass the real function
                func_regex_check=None,
                cache_postgres_schema=schema_cache,
                cache_postgres_buffer_create={},
                config_regex={},
                config_table={},
                config_obj_list_limit=1000,
                config_buffer_limit=100,
                mode="now",
                table="test_integration",
                obj_list=[{"title": "Integration Test Row"}],
                is_serialize=0
            )
            
            assert len(created_ids) == 1
            new_id = created_ids[0]
            
            # 5. Perform a real READ
            from core.function import func_postgres_where_build, func_postgres_relation
            rows = await func_postgres_read(
                client_postgres_pool=pool,
                client_password_hasher=hasher,
                func_postgres_serialize=func_postgres_serialize, 
                func_postgres_where_build=func_postgres_where_build,
                func_postgres_relation=func_postgres_relation,
                cache_postgres_schema=schema_cache,
                config_relation_fetch_limit_max=1000,
                table="test_integration",
                filter_obj={"id": f"=,{int(new_id)}"},
                limit=10,
                page=1,
                order="id desc",
                column="*",
                relation=None
            )
            
            assert len(rows) == 1
            assert rows[0]["title"] == "Integration Test Row"
            print("\n✅ Standalone Postgres: E2E Lifecycle (Schema -> Create -> Read) successful.")

        finally:
            await pool.close()
