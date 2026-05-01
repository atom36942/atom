import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# ---------------------------------------------------------------------------
# Orchestrator Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_func_orchestrator_obj_create_admin():
    from core.function.orchestrator import func_orchestrator_obj_create
    mock_pool = AsyncMock()
    mock_create = AsyncMock()
    mock_create.return_value = 100 # id
    
    res = await func_orchestrator_obj_create(
        user_id=1, api_role="admin", table="users", mode="create",
        is_serialize=1, queue=None, obj_list=[{"id": 100}],
        config_table_create_my=[], config_table_create_public=[],
        config_column_blocked=[], config_table={}, config_regex={},
        func_regex_check=AsyncMock(), client_celery_producer=None,
        client_kafka_producer=None, client_rabbitmq_producer=None,
        client_redis_producer=None, func_orchestrator_producer=AsyncMock(),
        func_postgres_create=mock_create, client_postgres_pool=mock_pool,
        client_password_hasher=None, func_postgres_serialize=AsyncMock(),
        cache_postgres_schema={"users": {"id": {"datatype": "int"}}},
        cache_postgres_buffer={}, client_postgres_conn=None
    )
    assert res == 100
    mock_create.assert_called_once()

@pytest.mark.asyncio
async def test_func_orchestrator_obj_create_my_blocked():
    from core.function.orchestrator import func_orchestrator_obj_create
    
    # Test 'my' mode with table NOT in allowed list
    with pytest.raises(Exception, match="table not allowed for role 'my'"):
        await func_orchestrator_obj_create(
            user_id=2, api_role="my", table="secret_table", mode="create",
            is_serialize=1, queue=None, obj_list=[{"k": "v"}],
            config_table_create_my=["allowed_table"], 
            config_table_create_public=[], config_column_blocked=[],
            config_table={}, config_regex={}, func_regex_check=AsyncMock(),
            client_celery_producer=None, client_kafka_producer=None,
            client_rabbitmq_producer=None, client_redis_producer=None,
            func_orchestrator_producer=AsyncMock(), func_postgres_create=AsyncMock(),
            client_postgres_pool=None, client_password_hasher=None,
            func_postgres_serialize=AsyncMock(), cache_postgres_schema={},
            cache_postgres_buffer={}, client_postgres_conn=None
        )

@pytest.mark.asyncio
async def test_func_orchestrator_obj_create_queue_dispatch():
    from core.function.orchestrator import func_orchestrator_obj_create
    mock_producer_func = AsyncMock()
    mock_producer_func.return_value = "logs queued"
    
    # Test queue dispatch
    res = await func_orchestrator_obj_create(
        user_id=1, api_role="admin", table="logs", mode="create",
        is_serialize=1, queue="celery", obj_list=[{"msg": "test"}],
        config_table_create_my=[], config_table_create_public=[],
        config_column_blocked=[], config_table={},
        config_regex={}, func_regex_check=AsyncMock(),
        client_celery_producer=MagicMock(), client_kafka_producer=None,
        client_rabbitmq_producer=None, client_redis_producer=None,
        func_orchestrator_producer=mock_producer_func, 
        func_postgres_create=AsyncMock(), client_postgres_pool=None,
        client_password_hasher=None, func_postgres_serialize=AsyncMock(),
        cache_postgres_schema={"logs": {"id": {"datatype": "int"}}},
        cache_postgres_buffer={}, client_postgres_conn=None
    )
    assert res == "logs queued"
    mock_producer_func.assert_called_once()
