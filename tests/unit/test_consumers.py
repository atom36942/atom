import sys
import os
from pathlib import Path
import pytest
import orjson
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.consumer.postgres_create import execute as execute_create
from core.consumer.postgres_update import execute as execute_update
from core.consumer.base_broker import func_consumer_failed_payload_log

@pytest.mark.asyncio
async def test_postgres_create_consumer_execute_calls_core_function():
    client_postgres_pool = MagicMock()
    payload = {
        "table": "test_table",
        "mode": "buffer",
        "obj_list": [{"id": 1, "data": "test"}]
    }
    cache_postgres_buffer_create = {}
    cache_postgres_schema = {"test_table": {"id": {"datatype": "int"}}}
    client_password_hasher = MagicMock()

    with patch("core.consumer.postgres_create.func_postgres_create", new_callable=AsyncMock) as mock_func_create:
        mock_func_create.return_value = [1]
        
        result = await execute_create(
            client_postgres_pool, 
            payload, 
            cache_postgres_buffer_create, 
            cache_postgres_schema, 
            client_password_hasher
        )
        
        assert result == [1]
        mock_func_create.assert_called_once()
        args = mock_func_create.call_args.kwargs
        assert args["table"] == "test_table"
        assert args["mode"] == "buffer"
        assert args["obj_list"] == [{"id": 1, "data": "test"}]

@pytest.mark.asyncio
async def test_postgres_update_consumer_execute_calls_core_function():
    client_postgres_pool = MagicMock()
    payload = {
        "table": "test_table",
        "obj_list": [{"id": 1, "data": "updated"}],
        "created_by_id": 10
    }
    cache_postgres_buffer_create = {}
    cache_postgres_schema = {"test_table": {"id": {"datatype": "int"}}}
    client_password_hasher = MagicMock()

    with patch("core.consumer.postgres_update.func_postgres_update", new_callable=AsyncMock) as mock_func_update:
        mock_func_update.return_value = "OK"
        
        result = await execute_update(
            client_postgres_pool, 
            payload, 
            cache_postgres_buffer_create, 
            cache_postgres_schema, 
            client_password_hasher
        )
        
        assert result == "OK"
        mock_func_update.assert_called_once()
        args = mock_func_update.call_args.kwargs
        assert args["table"] == "test_table"
        assert args["obj_list"] == [{"id": 1, "data": "updated"}]
        assert args["created_by_id"] == 10

def test_func_consumer_failed_payload_log_writes_to_file():
    log_file = "tmp/consumer_failed_payload.jsonl"
    if os.path.exists(log_file):
        os.remove(log_file)
    
    error = Exception("test error")
    payload = {"key": "value"}
    
    func_consumer_failed_payload_log(
        queue="test_queue",
        channel="test_channel",
        payload=payload,
        error=error
    )
    
    assert os.path.exists(log_file)
    with open(log_file, "rb") as f:
        line = f.readline()
        record = orjson.loads(line)
        
    assert record["queue"] == "test_queue"
    assert record["channel"] == "test_channel"
    assert record["payload"] == payload
    assert record["error"] == "test error"
    assert "traceback" in record
