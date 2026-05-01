import pytest
from tests.conftest import unique_id
from core.consumer.postgres_create import execute as create_execute
from core.consumer.postgres_update import execute as update_execute

# ===========================================================================
# postgres_create consumer
# ===========================================================================
@pytest.mark.asyncio
async def test_consumer_create_single(state, db_available):
    uid = unique_id()
    payload = {
        "table": "test",
        "obj_list": [{"title": f"consumer_create_{uid}"}],
        "is_serialize": 0,
        "mode": "now"
    }
    result = await create_execute(
        state.client_postgres_pool, payload, {},
        state.cache_postgres_schema, state.client_password_hasher
    )
    assert isinstance(result, list)
    assert len(result) == 1

@pytest.mark.asyncio
async def test_consumer_create_bulk(state, db_available):
    uid = unique_id()
    payload = {
        "table": "test",
        "obj_list": [{"title": f"consumer_bulk_{uid}_{i}"} for i in range(3)],
        "is_serialize": 0,
        "mode": "now"
    }
    result = await create_execute(
        state.client_postgres_pool, payload, {},
        state.cache_postgres_schema, state.client_password_hasher
    )
    assert isinstance(result, list)
    assert len(result) == 3

# ===========================================================================
# postgres_update consumer
# ===========================================================================
@pytest.mark.asyncio
async def test_consumer_update(state, db_available):
    uid = unique_id()
    # Create first
    create_payload = {
        "table": "test",
        "obj_list": [{"title": f"consumer_upd_before_{uid}"}],
        "is_serialize": 0,
        "mode": "now"
    }
    ids = await create_execute(
        state.client_postgres_pool, create_payload, {},
        state.cache_postgres_schema, state.client_password_hasher
    )

    # Update
    update_payload = {
        "table": "test",
        "obj_list": [{"id": ids[0], "title": f"consumer_upd_after_{uid}"}],
        "is_serialize": 0,
        "created_by_id": None,
        "is_return_ids": 0
    }
    result = await update_execute(
        state.client_postgres_pool, update_payload, {},
        state.cache_postgres_schema, state.client_password_hasher
    )
    assert "1 rows updated" in str(result)
