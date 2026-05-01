import pytest
from datetime import datetime, date
from core.function.postgres_schema import func_postgres_serialize

# ===========================================================================
# Integer types
# ===========================================================================
@pytest.mark.asyncio
async def test_serialize_smallint(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"type": {"datatype": "smallint"}}}, table="test",
        obj_list=[{"type": "5"}], is_base=1
    )
    assert result[0]["type"] == 5
    assert isinstance(result[0]["type"], int)

@pytest.mark.asyncio
async def test_serialize_bigint(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"big_id": {"datatype": "bigint"}}}, table="test",
        obj_list=[{"big_id": "9999999999"}], is_base=1
    )
    assert result[0]["big_id"] == 9999999999

@pytest.mark.asyncio
async def test_serialize_serial(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"seq": {"datatype": "serial"}}}, table="test",
        obj_list=[{"seq": "42"}], is_base=1
    )
    assert result[0]["seq"] == 42

# ===========================================================================
# Float / Numeric
# ===========================================================================
@pytest.mark.asyncio
async def test_serialize_numeric(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"price": {"datatype": "numeric"}}}, table="test",
        obj_list=[{"price": "19.99"}], is_base=1
    )
    assert result[0]["price"] == 19.99

@pytest.mark.asyncio
async def test_serialize_double(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"val": {"datatype": "double precision"}}}, table="test",
        obj_list=[{"val": "3.14159"}], is_base=1
    )
    assert abs(result[0]["val"] - 3.14159) < 0.001

# ===========================================================================
# Boolean
# ===========================================================================
@pytest.mark.asyncio
async def test_serialize_bool_true(state):
    for val in ("true", "1", "yes", "on", "ok"):
        result = await func_postgres_serialize(
            client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
            cache_postgres_schema={"test": {"flag": {"datatype": "bool"}}}, table="test",
            obj_list=[{"flag": val}], is_base=1
        )
        assert result[0]["flag"] == 1, f"'{val}' should cast to 1"

@pytest.mark.asyncio
async def test_serialize_bool_false(state):
    for val in ("false", "0", "no", "off"):
        result = await func_postgres_serialize(
            client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
            cache_postgres_schema={"test": {"flag": {"datatype": "bool"}}}, table="test",
            obj_list=[{"flag": val}], is_base=1
        )
        assert result[0]["flag"] == 0, f"'{val}' should cast to 0"

# ===========================================================================
# Text
# ===========================================================================
@pytest.mark.asyncio
async def test_serialize_text_unchanged(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"title": {"datatype": "text"}}}, table="test",
        obj_list=[{"title": "hello world"}], is_base=1
    )
    assert result[0]["title"] == "hello world"

# ===========================================================================
# Timestamp
# ===========================================================================
@pytest.mark.asyncio
async def test_serialize_timestamptz_iso(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"created_at": {"datatype": "timestamptz"}}}, table="test",
        obj_list=[{"created_at": "2025-01-15T10:30:00Z"}], is_base=1
    )
    assert isinstance(result[0]["created_at"], datetime)

@pytest.mark.asyncio
async def test_serialize_timestamptz_offset(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"created_at": {"datatype": "timestamptz"}}}, table="test",
        obj_list=[{"created_at": "2025-01-15T10:30:00+05:30"}], is_base=1
    )
    assert isinstance(result[0]["created_at"], datetime)

@pytest.mark.asyncio
async def test_serialize_timestamptz_native(state):
    now = datetime.now()
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"created_at": {"datatype": "timestamptz"}}}, table="test",
        obj_list=[{"created_at": now}], is_base=1
    )
    assert result[0]["created_at"] == now

# ===========================================================================
# Date
# ===========================================================================
@pytest.mark.asyncio
async def test_serialize_date_iso(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"dob": {"datatype": "date"}}}, table="test",
        obj_list=[{"dob": "2000-06-15"}], is_base=1
    )
    assert isinstance(result[0]["dob"], date)
    assert result[0]["dob"].year == 2000

@pytest.mark.asyncio
async def test_serialize_date_native(state):
    today = date.today()
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"dob": {"datatype": "date"}}}, table="test",
        obj_list=[{"dob": today}], is_base=1
    )
    assert result[0]["dob"] == today

# ===========================================================================
# Array types
# ===========================================================================
@pytest.mark.asyncio
async def test_serialize_text_array_from_csv(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"tag": {"datatype": "text[]"}}}, table="test",
        obj_list=[{"tag": "alpha,beta,gamma"}], is_base=1
    )
    assert result[0]["tag"] == ["alpha", "beta", "gamma"]

@pytest.mark.asyncio
async def test_serialize_text_array_from_list(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"tag": {"datatype": "text[]"}}}, table="test",
        obj_list=[{"tag": ["a", "b"]}], is_base=1
    )
    assert result[0]["tag"] == ["a", "b"]

@pytest.mark.asyncio
async def test_serialize_int_array(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"tag_int": {"datatype": "integer[]"}}}, table="test",
        obj_list=[{"tag_int": "1,2,3"}], is_base=1
    )
    assert result[0]["tag_int"] == [1, 2, 3]

@pytest.mark.asyncio
async def test_serialize_bigint_array(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"tag_bigint": {"datatype": "bigint[]"}}}, table="test",
        obj_list=[{"tag_bigint": "1000000,2000000"}], is_base=1
    )
    assert result[0]["tag_bigint"] == [1000000, 2000000]

@pytest.mark.asyncio
async def test_serialize_empty_array(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"tag": {"datatype": "text[]"}}}, table="test",
        obj_list=[{"tag": ""}], is_base=1
    )
    assert result[0]["tag"] == []

# ===========================================================================
# JSONB
# ===========================================================================
@pytest.mark.asyncio
async def test_serialize_jsonb_dict_base(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"metadata": {"datatype": "jsonb"}}}, table="test",
        obj_list=[{"metadata": {"key": "val"}}], is_base=1
    )
    assert isinstance(result[0]["metadata"], str)
    assert "key" in result[0]["metadata"]

@pytest.mark.asyncio
async def test_serialize_jsonb_dict_non_base(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"metadata": {"datatype": "jsonb"}}}, table="test",
        obj_list=[{"metadata": {"key": "val"}}], is_base=0
    )
    assert isinstance(result[0]["metadata"], dict)

@pytest.mark.asyncio
async def test_serialize_jsonb_string_base(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"metadata": {"datatype": "jsonb"}}}, table="test",
        obj_list=[{"metadata": '{"key":"val"}'}], is_base=1
    )
    assert result[0]["metadata"] == '{"key":"val"}'

@pytest.mark.asyncio
async def test_serialize_jsonb_string_non_base(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"metadata": {"datatype": "jsonb"}}}, table="test",
        obj_list=[{"metadata": '{"key":"val"}'}], is_base=0
    )
    assert isinstance(result[0]["metadata"], dict)
    assert result[0]["metadata"]["key"] == "val"

# ===========================================================================
# Bytea
# ===========================================================================
@pytest.mark.asyncio
async def test_serialize_bytea_string(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"data": {"datatype": "bytea"}}}, table="test",
        obj_list=[{"data": "binary_data"}], is_base=0
    )
    assert isinstance(result[0]["data"], bytes)

@pytest.mark.asyncio
async def test_serialize_bytea_bytes(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"data": {"datatype": "bytea"}}}, table="test",
        obj_list=[{"data": b"raw_bytes"}], is_base=0
    )
    assert result[0]["data"] == b"raw_bytes"

# ===========================================================================
# Password hashing (users table)
# ===========================================================================
@pytest.mark.asyncio
async def test_serialize_password_hashed(state):
    schema = state.cache_postgres_schema if state.cache_postgres_schema and "users" in state.cache_postgres_schema else {"users": {"password": {"datatype": "text"}}}
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema=schema, table="users",
        obj_list=[{"password": "plain_pass"}], is_base=1
    )
    assert result[0]["password"] != "plain_pass"
    assert result[0]["password"].startswith("$argon2")

@pytest.mark.asyncio
async def test_serialize_password_none(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema=state.cache_postgres_schema, table="users",
        obj_list=[{"password": None}], is_base=1
    )
    assert result[0]["password"] is None

# ===========================================================================
# Null handling
# ===========================================================================
@pytest.mark.asyncio
async def test_serialize_null_value(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"title": {"datatype": "text"}}}, table="test",
        obj_list=[{"title": None}], is_base=1
    )
    assert result[0]["title"] is None

@pytest.mark.asyncio
async def test_serialize_null_string_in_int(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"type": {"datatype": "int"}}}, table="test",
        obj_list=[{"type": "null"}], is_base=1
    )
    assert result[0]["type"] is None

# ===========================================================================
# Unknown table passthrough
# ===========================================================================
@pytest.mark.asyncio
async def test_serialize_unknown_table(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={}, table="nonexistent",
        obj_list=[{"col": "val"}], is_base=0
    )
    assert result == [{"col": "val"}]

# ===========================================================================
# Unknown column skipped
# ===========================================================================
@pytest.mark.asyncio
async def test_serialize_unknown_column_skipped(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"title": {"datatype": "text"}}}, table="test",
        obj_list=[{"title": "hello", "nonexistent_col": "val"}], is_base=1
    )
    assert "title" in result[0]
    assert "nonexistent_col" not in result[0]

# ===========================================================================
# Multiple objects
# ===========================================================================
@pytest.mark.asyncio
async def test_serialize_multiple_objects(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"type": {"datatype": "int"}, "title": {"datatype": "text"}}}, table="test",
        obj_list=[{"type": "1", "title": "a"}, {"type": "2", "title": "b"}], is_base=1
    )
    assert len(result) == 2
    assert result[0]["type"] == 1
    assert result[1]["type"] == 2

# ===========================================================================
# ID passthrough
# ===========================================================================
@pytest.mark.asyncio
async def test_serialize_id_passthrough(state):
    result = await func_postgres_serialize(
        client_postgres_pool=state.client_postgres_pool, client_password_hasher=state.client_password_hasher,
        cache_postgres_schema={"test": {"title": {"datatype": "text"}}}, table="test",
        obj_list=[{"id": 42, "title": "hello"}], is_base=1
    )
    assert result[0]["id"] == 42
