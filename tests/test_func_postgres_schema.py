import pytest
import copy
from tests.conftest import unique_id
from core.function.postgres_schema import func_postgres_schema_read, func_postgres_serialize, func_postgres_schema_init

# ===========================================================================
# Schema read
# ===========================================================================
@pytest.mark.asyncio
async def test_schema_read_returns_dict(state, db_available):
    schema = await func_postgres_schema_read(client_postgres_pool=state.client_postgres_pool)
    assert isinstance(schema, dict)
    assert "users" in schema
    assert "test" in schema
    assert "id" in schema["users"]

# ===========================================================================
# Serialize: type casting
# ===========================================================================
@pytest.mark.asyncio
async def test_serialize_int(state, db_available):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema=state.cache_postgres_schema, table="test",
        obj_list=[{"type": "5"}], is_base=1
    )
    assert result[0]["type"] == 5

@pytest.mark.asyncio
async def test_serialize_text(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema=state.cache_postgres_schema, table="test",
        obj_list=[{"title": "hello"}], is_base=1
    )
    assert result[0]["title"] == "hello"

@pytest.mark.asyncio
async def test_serialize_array(state, db_available):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema=state.cache_postgres_schema, table="test",
        obj_list=[{"tag": "alpha,beta,gamma"}], is_base=1
    )
    assert isinstance(result[0]["tag"], list)
    assert len(result[0]["tag"]) == 3

@pytest.mark.asyncio
async def test_serialize_jsonb(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema=state.cache_postgres_schema, table="test",
        obj_list=[{"metadata": {"key": "value"}}], is_base=0
    )
    assert isinstance(result[0]["metadata"], dict)

@pytest.mark.asyncio
async def test_serialize_password_hash(state, db_available):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema=state.cache_postgres_schema, table="users",
        obj_list=[{"password": "plaintext123"}], is_base=1
    )
    assert result[0]["password"] != "plaintext123"
    assert result[0]["password"].startswith("$argon2")

@pytest.mark.asyncio
async def test_serialize_unknown_table(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema=state.cache_postgres_schema, table="nonexistent_table",
        obj_list=[{"col": "val"}], is_base=0
    )
    assert result == [{"col": "val"}]

@pytest.mark.asyncio
async def test_serialize_null_value(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema=state.cache_postgres_schema, table="test",
        obj_list=[{"title": None}], is_base=1
    )
    assert result[0]["title"] is None

# ===========================================================================
# Schema init: add column
# ===========================================================================
@pytest.mark.asyncio
async def test_schema_init_add_column(state, db_available):
    uid = unique_id()
    col_name = f"test_col_{uid}"
    test_config = copy.deepcopy(state.config_postgres)
    test_config["table"]["test"].append({"name": col_name, "datatype": "text", "is_mandatory": 0})
    await func_postgres_schema_init(
        client_postgres_pool=state.client_postgres_pool,
        client_password_hasher=state.client_password_hasher,
        config_postgres=test_config,
        config_postgres_root_user_password=state.config_postgres_root_user_password
    )
    schema = await func_postgres_schema_read(client_postgres_pool=state.client_postgres_pool)
    assert col_name in schema["test"]

# ===========================================================================
# Schema init: add and remove index
# ===========================================================================
@pytest.mark.asyncio
async def test_schema_init_add_remove_index(state, db_available):
    uid = unique_id()
    col_name = f"test_idx_col_{uid}"
    idx_name = f"idx_test_{col_name}_btree"

    # Add column + index
    test_config = copy.deepcopy(state.config_postgres)
    test_config["table"]["test"].append({"name": col_name, "datatype": "text", "index": f"btree({col_name})"})
    await func_postgres_schema_init(
        client_postgres_pool=state.client_postgres_pool,
        client_password_hasher=state.client_password_hasher,
        config_postgres=test_config,
        config_postgres_root_user_password=state.config_postgres_root_user_password
    )
    async with state.client_postgres_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT indexname FROM pg_indexes WHERE indexname=$1", idx_name)
        assert row is not None

    # Remove index from config
    test_config_no_idx = copy.deepcopy(test_config)
    test_config_no_idx["table"]["test"][-1].pop("index")
    await func_postgres_schema_init(
        client_postgres_pool=state.client_postgres_pool,
        client_password_hasher=state.client_password_hasher,
        config_postgres=test_config_no_idx,
        config_postgres_root_user_password=state.config_postgres_root_user_password
    )
    async with state.client_postgres_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT indexname FROM pg_indexes WHERE indexname=$1", idx_name)
        assert row is None
