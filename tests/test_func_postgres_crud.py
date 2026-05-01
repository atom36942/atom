import pytest
from tests.conftest import unique_id
from core.function.postgres_crud import func_postgres_create, func_postgres_read, func_postgres_update, func_postgres_delete

# ===========================================================================
# Create
# ===========================================================================
@pytest.mark.asyncio
async def test_create_single_now(state, db_available):
    uid = unique_id()
    ids = await func_postgres_create(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        mode="now", table="test", obj_list=[{"title": f"crud_single_{uid}"}],
        is_serialize=0, buffer_limit=0, cache_postgres_buffer=state.cache_postgres_buffer, client_postgres_conn=None
    )
    assert isinstance(ids, list)
    assert len(ids) == 1
    assert isinstance(ids[0], int)

@pytest.mark.asyncio
async def test_create_bulk_now(state, db_available):
    uid = unique_id()
    obj_list = [{"title": f"crud_bulk_{uid}_{i}"} for i in range(5)]
    ids = await func_postgres_create(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        mode="now", table="test", obj_list=obj_list,
        is_serialize=0, buffer_limit=0, cache_postgres_buffer=state.cache_postgres_buffer, client_postgres_conn=None
    )
    assert len(ids) == 5

@pytest.mark.asyncio
async def test_create_buffer(state):
    uid = unique_id()
    buffer = {}
    result = await func_postgres_create(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        mode="buffer", table="test", obj_list=[{"title": f"buf_{uid}"}],
        is_serialize=0, buffer_limit=100, cache_postgres_buffer=buffer, client_postgres_conn=None
    )
    assert result == "buffered"
    assert len(buffer.get("test", [])) == 1

@pytest.mark.asyncio
async def test_create_flush(state, db_available):
    buffer = {"test": [{"title": "flush_item"}]}
    result = await func_postgres_create(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        mode="flush", table="", obj_list=[],
        is_serialize=0, buffer_limit=0, cache_postgres_buffer=buffer, client_postgres_conn=None
    )
    assert result == "flushed"
    assert buffer["test"] == []

@pytest.mark.asyncio
async def test_create_with_serialize(state, db_available):
    uid = unique_id()
    ids = await func_postgres_create(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        mode="now", table="test", obj_list=[{"title": f"ser_{uid}", "type": "1"}],
        is_serialize=1, buffer_limit=0, cache_postgres_buffer=state.cache_postgres_buffer, client_postgres_conn=None
    )
    assert isinstance(ids, list)
    assert len(ids) == 1

@pytest.mark.asyncio
async def test_create_invalid_identifier(state):
    with pytest.raises(Exception, match="invalid identifier"):
        await func_postgres_create(
            client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
            func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
            mode="now", table="test", obj_list=[{"title; DROP TABLE test--": "hack"}],
            is_serialize=0, buffer_limit=0, cache_postgres_buffer=state.cache_postgres_buffer, client_postgres_conn=None
        )

@pytest.mark.asyncio
async def test_create_empty_list(state):
    result = await func_postgres_create(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        mode="now", table="test", obj_list=[],
        is_serialize=0, buffer_limit=0, cache_postgres_buffer=state.cache_postgres_buffer, client_postgres_conn=None
    )
    assert result is None

@pytest.mark.asyncio
async def test_create_unsupported_mode(state):
    result = await func_postgres_create(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        mode="invalid", table="test", obj_list=[{"title": "test"}],
        is_serialize=0, buffer_limit=0, cache_postgres_buffer=state.cache_postgres_buffer, client_postgres_conn=None
    )
    assert result == "unsupported mode"

# ===========================================================================
# Read
# ===========================================================================
@pytest.mark.asyncio
async def test_read_basic(state, db_available):
    rows = await func_postgres_read(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        table="test", filter_obj={}, limit=5, page=1, order="id desc", column="*", creator_key=None, action_key=None
    )
    assert isinstance(rows, list)

@pytest.mark.asyncio
async def test_read_filter_equals(state, db_available):
    uid = unique_id()
    title = f"readfilt_{uid}"
    await func_postgres_create(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        mode="now", table="test", obj_list=[{"title": title}],
        is_serialize=0, buffer_limit=0, cache_postgres_buffer=state.cache_postgres_buffer, client_postgres_conn=None
    )
    rows = await func_postgres_read(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        table="test", filter_obj={"title": f"=,{title}"}, limit=10, page=1, order="id desc", column="*", creator_key=None, action_key=None
    )
    assert len(rows) >= 1
    assert rows[0]["title"] == title

@pytest.mark.asyncio
async def test_read_pagination(state, db_available):
    rows_p1 = await func_postgres_read(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        table="test", filter_obj={}, limit=2, page=1, order="id asc", column="*", creator_key=None, action_key=None
    )
    rows_p2 = await func_postgres_read(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        table="test", filter_obj={}, limit=2, page=2, order="id asc", column="*", creator_key=None, action_key=None
    )
    if rows_p1 and rows_p2:
        assert rows_p1[0]["id"] != rows_p2[0]["id"]

@pytest.mark.asyncio
async def test_read_invalid_identifier(state):
    with pytest.raises(Exception, match="invalid identifier"):
        await func_postgres_read(
            client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
            func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
            table="test; DROP TABLE users", filter_obj={}, limit=5, page=1, order="id desc", column="*", creator_key=None, action_key=None
        )

# ===========================================================================
# Update
# ===========================================================================
@pytest.mark.asyncio
async def test_update_single(state, db_available):
    uid = unique_id()
    ids = await func_postgres_create(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        mode="now", table="test", obj_list=[{"title": f"upd_before_{uid}"}],
        is_serialize=0, buffer_limit=0, cache_postgres_buffer=state.cache_postgres_buffer, client_postgres_conn=None
    )
    result = await func_postgres_update(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        table="test", obj_list=[{"id": ids[0], "title": f"upd_after_{uid}"}],
        is_serialize=0, created_by_id=None, is_return_ids=0, client_postgres_conn=None
    )
    assert "1 rows updated" in result

@pytest.mark.asyncio
async def test_update_missing_id(state):
    with pytest.raises(Exception, match="missing required field.*id"):
        await func_postgres_update(
            client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
            func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
            table="test", obj_list=[{"title": "no_id"}],
            is_serialize=0, created_by_id=None, is_return_ids=0, client_postgres_conn=None
        )

# ===========================================================================
# Delete
# ===========================================================================
@pytest.mark.asyncio
async def test_delete_by_ids(state, db_available):
    uid = unique_id()
    ids = await func_postgres_create(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        func_postgres_serialize=state.func_postgres_serialize, cache_postgres_schema=state.cache_postgres_schema,
        mode="now", table="test", obj_list=[{"title": f"del_{uid}"}],
        is_serialize=0, buffer_limit=0, cache_postgres_buffer=state.cache_postgres_buffer, client_postgres_conn=None
    )
    result = await func_postgres_delete(
        client_postgres_pool=state.client_postgres_pool, table="test", ids=str(ids[0]),
        created_by_id=None, client_postgres_conn=None
    )
    assert result == "ids deleted"

@pytest.mark.asyncio
async def test_delete_users_table_blocked(state):
    with pytest.raises(Exception, match="users table not allowed"):
        await func_postgres_delete(
            client_postgres_pool=state.client_postgres_pool, table="users", ids="999999",
            created_by_id=None, client_postgres_conn=None
        )
