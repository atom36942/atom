import pytest
from tests.conftest import unique_id
from core.function.orchestrator import func_orchestrator_obj_create, func_orchestrator_obj_update, func_orchestrator_producer

# ===========================================================================
# Create: role-based access
# ===========================================================================
@pytest.mark.asyncio
async def test_create_admin_any_table(state, db_available):
    uid = unique_id()
    result = await func_orchestrator_obj_create(
        user_id=1, api_role="admin", table="test", mode="now", is_serialize=0, queue=None,
        obj_list=[{"title": f"orch_admin_{uid}"}],
        config_table_create_disable_my=state.config_table_create_disable_my, config_table_create_enable_public=state.config_table_create_enable_public,
        config_column_disable=state.config_column_disable, config_table=state.config_table,
        config_regex=state.config_regex, func_regex_check=state.func_regex_check,
        client_celery_producer=state.client_celery_producer, client_kafka_producer=state.client_kafka_producer,
        client_rabbitmq_producer=state.client_rabbitmq_producer, client_redis_producer=state.client_redis_producer,
        func_orchestrator_producer=state.func_orchestrator_producer, func_postgres_create=state.func_postgres_create,
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        cache_postgres_buffer=state.cache_postgres_buffer, client_postgres_conn=None
    )
    assert isinstance(result, list)
    assert len(result) >= 1

@pytest.mark.asyncio
async def test_create_my_allowed_table(state, db_available):
    uid = unique_id()
    result = await func_orchestrator_obj_create(
        user_id=2, api_role="my", table="test", mode="now", is_serialize=0, queue=None,
        obj_list=[{"title": f"orch_my_{uid}"}],
        config_table_create_disable_my=state.config_table_create_disable_my, config_table_create_enable_public=state.config_table_create_enable_public,
        config_column_disable=state.config_column_disable, config_table=state.config_table,
        config_regex=state.config_regex, func_regex_check=state.func_regex_check,
        client_celery_producer=state.client_celery_producer, client_kafka_producer=state.client_kafka_producer,
        client_rabbitmq_producer=state.client_rabbitmq_producer, client_redis_producer=state.client_redis_producer,
        func_orchestrator_producer=state.func_orchestrator_producer, func_postgres_create=state.func_postgres_create,
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        cache_postgres_buffer=state.cache_postgres_buffer, client_postgres_conn=None
    )
    assert isinstance(result, list)

@pytest.mark.asyncio
async def test_create_my_disabled_table(state):
    with pytest.raises(Exception, match="table not allowed for role 'my'"):
        await func_orchestrator_obj_create(
            user_id=2, api_role="my", table="users", mode="now", is_serialize=0, queue=None,
            obj_list=[{"username": "hack"}],
            config_table_create_disable_my=state.config_table_create_disable_my, config_table_create_enable_public=state.config_table_create_enable_public,
            config_column_disable=state.config_column_disable, config_table=state.config_table,
            config_regex=state.config_regex, func_regex_check=state.func_regex_check,
            client_celery_producer=state.client_celery_producer, client_kafka_producer=state.client_kafka_producer,
            client_rabbitmq_producer=state.client_rabbitmq_producer, client_redis_producer=state.client_redis_producer,
            func_orchestrator_producer=state.func_orchestrator_producer, func_postgres_create=state.func_postgres_create,
            client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
            func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
            cache_postgres_buffer=state.cache_postgres_buffer, client_postgres_conn=None
        )

@pytest.mark.asyncio
async def test_create_public_disabled_table(state):
    with pytest.raises(Exception, match="table not allowed for role 'public'"):
        await func_orchestrator_obj_create(
            user_id=None, api_role="public", table="users", mode="now", is_serialize=0, queue=None,
            obj_list=[{"username": "hack"}],
            config_table_create_disable_my=state.config_table_create_disable_my, config_table_create_enable_public=state.config_table_create_enable_public,
            config_column_disable=state.config_column_disable, config_table=state.config_table,
            config_regex=state.config_regex, func_regex_check=state.func_regex_check,
            client_celery_producer=state.client_celery_producer, client_kafka_producer=state.client_kafka_producer,
            client_rabbitmq_producer=state.client_rabbitmq_producer, client_redis_producer=state.client_redis_producer,
            func_orchestrator_producer=state.func_orchestrator_producer, func_postgres_create=state.func_postgres_create,
            client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
            func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
            cache_postgres_buffer=state.cache_postgres_buffer, client_postgres_conn=None
        )

# ===========================================================================
# Create: blocked columns
# ===========================================================================
@pytest.mark.asyncio
async def test_create_disabled_column_non_admin(state):
    with pytest.raises(Exception, match="restricted"):
        await func_orchestrator_obj_create(
            user_id=2, api_role="my", table="test", mode="now", is_serialize=0, queue=None,
            obj_list=[{"title": "test", "is_active": 1}],
            config_table_create_disable_my=state.config_table_create_disable_my, config_table_create_enable_public=state.config_table_create_enable_public,
            config_column_disable=state.config_column_disable, config_table=state.config_table,
            config_regex=state.config_regex, func_regex_check=state.func_regex_check,
            client_celery_producer=state.client_celery_producer, client_kafka_producer=state.client_kafka_producer,
            client_rabbitmq_producer=state.client_rabbitmq_producer, client_redis_producer=state.client_redis_producer,
            func_orchestrator_producer=state.func_orchestrator_producer, func_postgres_create=state.func_postgres_create,
            client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
            func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
            cache_postgres_buffer=state.cache_postgres_buffer, client_postgres_conn=None
        )

# ===========================================================================
# Create: empty list
# ===========================================================================
@pytest.mark.asyncio
async def test_create_empty_list(state):
    with pytest.raises(Exception, match="object list required"):
        await func_orchestrator_obj_create(
            user_id=1, api_role="admin", table="test", mode="now", is_serialize=0, queue=None,
            obj_list=[],
            config_table_create_disable_my=state.config_table_create_disable_my, config_table_create_enable_public=state.config_table_create_enable_public,
            config_column_disable=state.config_column_disable, config_table=state.config_table,
            config_regex=state.config_regex, func_regex_check=state.func_regex_check,
            client_celery_producer=state.client_celery_producer, client_kafka_producer=state.client_kafka_producer,
            client_rabbitmq_producer=state.client_rabbitmq_producer, client_redis_producer=state.client_redis_producer,
            func_orchestrator_producer=state.func_orchestrator_producer, func_postgres_create=state.func_postgres_create,
            client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
            func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
            cache_postgres_buffer=state.cache_postgres_buffer, client_postgres_conn=None
        )

# ===========================================================================
# Create: sets created_by_id
# ===========================================================================
@pytest.mark.asyncio
async def test_create_injects_created_by_id(state, db_available):
    uid = unique_id()
    obj = [{"title": f"inject_{uid}"}]
    await func_orchestrator_obj_create(
        user_id=42, api_role="my", table="test", mode="now", is_serialize=0, queue=None,
        obj_list=obj,
        config_table_create_disable_my=state.config_table_create_disable_my, config_table_create_enable_public=state.config_table_create_enable_public,
        config_column_disable=state.config_column_disable, config_table=state.config_table,
        config_regex=state.config_regex, func_regex_check=state.func_regex_check,
        client_celery_producer=state.client_celery_producer, client_kafka_producer=state.client_kafka_producer,
        client_rabbitmq_producer=state.client_rabbitmq_producer, client_redis_producer=state.client_redis_producer,
        func_orchestrator_producer=state.func_orchestrator_producer, func_postgres_create=state.func_postgres_create,
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        cache_postgres_buffer=state.cache_postgres_buffer, client_postgres_conn=None
    )
    assert obj[0].get("created_by_id") == 42

# ===========================================================================
# Update: role checks
# ===========================================================================
@pytest.mark.asyncio
async def test_update_disabled_column_non_admin(state):
    with pytest.raises(Exception, match="restricted"):
        await func_orchestrator_obj_update(
            user_id=2, api_role="my", table="test", is_serialize=0, queue=None, otp=None,
            obj_list=[{"id": 1, "is_active": 1}],
            config_is_enable_otp_users_update_admin=0, config_column_disable=state.config_column_disable,
            config_column_enable_single_update=state.config_column_enable_single_update,
            config_regex=state.config_regex, func_regex_check=state.func_regex_check,
            func_otp_verify=state.func_otp_verify,
            client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
            config_expiry_sec_otp=state.config_expiry_sec_otp,
            client_celery_producer=state.client_celery_producer, client_kafka_producer=state.client_kafka_producer,
            client_rabbitmq_producer=state.client_rabbitmq_producer, client_redis_producer=state.client_redis_producer,
            func_orchestrator_producer=state.func_orchestrator_producer, func_postgres_update=state.func_postgres_update,
            func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
            client_postgres_conn=None
        )

# ===========================================================================
# Producer: invalid queue
# ===========================================================================
@pytest.mark.asyncio
async def test_producer_invalid_queue(state):
    with pytest.raises(Exception, match="invalid queue"):
        await func_orchestrator_producer(
            queue="invalid_queue", func_name="func_postgres_create",
            payload={}, client_celery_producer=None, client_kafka_producer=None,
            client_rabbitmq_producer=None, client_redis_producer=None
        )

@pytest.mark.asyncio
async def test_producer_missing_queue(state):
    with pytest.raises(Exception, match="queue missing"):
        await func_orchestrator_producer(
            queue="", func_name="func_postgres_create",
            payload={}, client_celery_producer=None, client_kafka_producer=None,
            client_rabbitmq_producer=None, client_redis_producer=None
        )
