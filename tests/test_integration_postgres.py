import pytest
import asyncio
from testcontainers.postgres import PostgresContainer
import asyncpg
from core.function import func_postgres_schema_init, func_postgres_create, func_postgres_read

@pytest.mark.asyncio
async def test_postgres_integration_lifecycle():
    # 1. Start a real Postgres container
    with PostgresContainer("postgres:16-alpine") as postgres:
        # Get the connection URL from the container
        conn_url = postgres.get_connection_url().replace("psycopg2", "postgresql")
        
        # 2. Create a connection pool to the real container
        pool = await asyncpg.create_pool(dsn=conn_url)
        
        try:
            # 3. Initialize the schema
            # We use your real config and real function!
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
            
            await func_postgres_schema_init(
                client_postgres_pool=pool,
                client_password_hasher=None, # Not needed for this table
                config_postgres=config_postgres,
                config_postgres_root_user_password="password"
            )
            
            # 4. Perform a real CREATE
            # Using your core function func_postgres_create
            created_ids = await func_postgres_create(
                client_postgres_pool=pool,
                table="test_integration",
                obj_list=[{"title": "Integration Test Row"}]
            )
            
            assert len(created_ids) == 1
            new_id = created_ids[0]
            
            # 5. Perform a real READ
            # Using your core function func_postgres_read
            rows = await func_postgres_read(
                client_postgres_pool=pool,
                table="test_integration",
                filter_obj={"id": f"=,{new_id}"}
            )
            
            assert len(rows) == 1
            assert rows[0]["title"] == "Integration Test Row"
            assert rows[0]["status"] == 1
            
            print(f"\n✅ Integration Test Success! Row ID {new_id} verified in real Postgres container.")
            
        finally:
            await pool.close()

if __name__ == "__main__":
    # If run directly
    asyncio.run(test_postgres_integration_lifecycle())
