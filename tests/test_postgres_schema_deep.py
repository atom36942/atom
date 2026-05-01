import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# ---------------------------------------------------------------------------
# Postgres Schema Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_func_postgres_schema_init_basic():
    from core.function.postgres_schema import func_postgres_schema_init
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    
    mock_conn.fetch.return_value = []
    mock_conn.fetchval.return_value = None
    
    # Correct format: table -> list of dicts
    config = {
        "table": {
            "test_table": [
                {"name": "id", "datatype": "bigint"}
            ]
        }
    }
    
    await func_postgres_schema_init(
        client_postgres_pool=mock_pool,
        client_password_hasher=MagicMock(),
        config_postgres=config,
        config_postgres_root_user_password="pass"
    )
    
    executed_sqls = [call.args[0] for call in mock_conn.execute.call_args_list]
    assert any("CREATE TABLE IF NOT EXISTS test_table" in sql for sql in executed_sqls)

@pytest.mark.asyncio
async def test_func_postgres_schema_read():
    from core.function.postgres_schema import func_postgres_schema_read
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    
    mock_conn.fetch.return_value = [
        {"table_name": "t1", "column_name": "c1", "datatype": "text", "is_mandatory": 0, "is_unique": 0, "index": None},
        {"table_name": "t1", "column_name": "c2", "datatype": "int", "is_mandatory": 1, "is_unique": 1, "index": "primary"}
    ]
    
    res = await func_postgres_schema_read(client_postgres_pool=mock_pool)
    assert "t1" in res
    assert "c1" in res["t1"]
    assert res["t1"]["c2"]["datatype"] == "int"

@pytest.mark.asyncio
async def test_func_postgres_serialize_base():
    from core.function.postgres_schema import func_postgres_serialize
    mock_pool = AsyncMock()
    schema = {"t1": {"id": {"datatype": "int"}, "name": {"datatype": "text"}}}
    res = await func_postgres_serialize(
        client_postgres_pool=mock_pool,
        client_password_hasher=MagicMock(),
        cache_postgres_schema=schema,
        table="t1",
        obj_list=[{"id": "1", "name": "foo"}],
        is_base=1
    )
    assert res[0]["id"] == 1
    assert res[0]["name"] == "foo"
