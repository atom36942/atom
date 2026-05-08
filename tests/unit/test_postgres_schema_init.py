import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.function import func_postgres_schema_init

@pytest.mark.asyncio
async def test_func_postgres_schema_init_basic_table_creation():
    client_postgres_pool = AsyncMock()
    client_password_hasher = MagicMock()
    config_postgres = {
        "table": {
            "test_table": [
                {"name": "id", "datatype": "serial", "is_primary": 1},
                {"name": "title", "datatype": "text"}
            ]
        },
        "extension": ["uuid-ossp"],
        "control": {
            "is_enable_extension": 1
        }
    }
    
    # Mock connection and transaction
    conn = AsyncMock()
    # acquire should be a regular mock that returns an async context manager
    client_postgres_pool.acquire = MagicMock()
    client_postgres_pool.acquire.return_value.__aenter__.return_value = conn
    
    # Mock schema check results (empty schema)
    # Using tuples to support r[0] access
    conn.fetch.side_effect = [
        [], # pg_extension
        [], # columns
        [], # pg_indexes
        [], # pg_constraint
        []  # pg_trigger
    ]
    
    await func_postgres_schema_init(
        client_postgres_pool=client_postgres_pool,
        client_password_hasher=client_password_hasher,
        config_postgres=config_postgres,
        config_postgres_root_user_password="password"
    )
    
    # Verify extensions were created
    conn.execute.assert_any_call('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    
    # Verify table was created
    create_table_call = [call for call in conn.execute.call_args_list if "CREATE TABLE IF NOT EXISTS" in call.args[0]]
    assert len(create_table_call) > 0
    assert 'test_table' in create_table_call[0].args[0]

@pytest.mark.asyncio
async def test_func_postgres_schema_init_adds_missing_column():
    client_postgres_pool = AsyncMock()
    client_password_hasher = MagicMock()
    config_postgres = {
        "table": {
            "test_table": [
                {"name": "id", "datatype": "serial", "is_primary": 1},
                {"name": "new_col", "datatype": "text"}
            ]
        }
    }
    
    conn = AsyncMock()
    client_postgres_pool.acquire = MagicMock()
    client_postgres_pool.acquire.return_value.__aenter__.return_value = conn
    
    # Mock schema: test_table exists but only has 'id'
    # Use tuples to support r[0] indexing
    conn.fetch.side_effect = [
        [], # pg_extension
        [("id", "integer", "YES", None)], # columns (attname, type, notnull, default)
        [], # pg_indexes
        [], # pg_constraint
        []  # pg_trigger
    ]
    
    await func_postgres_schema_init(
        client_postgres_pool=client_postgres_pool,
        client_password_hasher=client_password_hasher,
        config_postgres=config_postgres,
        config_postgres_root_user_password="password"
    )
    
    # Verify ALTER TABLE was called to add new_col
    conn.execute.assert_any_call('ALTER TABLE test_table ADD COLUMN new_col text  ')

@pytest.mark.asyncio
async def test_func_postgres_schema_init_raises_on_reserved_keyword():
    client_postgres_pool = AsyncMock()
    config_postgres = {
        "table": {
            "test_table": [
                {"name": "select", "datatype": "text"} # Reserved keyword
            ]
        }
    }
    
    with pytest.raises(Exception, match="is a PostgreSQL reserved keyword"):
        await func_postgres_schema_init(
            client_postgres_pool=client_postgres_pool,
            client_password_hasher=MagicMock(),
            config_postgres=config_postgres,
            config_postgres_root_user_password="password"
        )
