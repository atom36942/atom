import pytest
import time
import gzip
import base64
from unittest.mock import AsyncMock, MagicMock
from fastapi import Response
from core.function.app_request import func_request_param_read, func_request_obj_list_read, func_check_cache

# ===========================================================================
# func_request_param_read: mode validation
# ===========================================================================
@pytest.mark.asyncio
async def test_param_read_invalid_mode():
    req = MagicMock()
    with pytest.raises(Exception, match="invalid mode"):
        await func_request_param_read(request=req, mode="invalid", strict=0, config=None)

@pytest.mark.asyncio
async def test_param_read_query_mode():
    req = MagicMock()
    req.query_params = {"table": "test", "limit": "10"}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    result = await func_request_param_read(request=req, mode="query", strict=0, config=None)
    assert result["table"] == "test"
    assert result["limit"] == "10"

@pytest.mark.asyncio
async def test_param_read_body_mode():
    req = MagicMock()
    req.json = AsyncMock(return_value={"title": "hello", "type": 1})
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    result = await func_request_param_read(request=req, mode="body", strict=0, config=None)
    assert result["title"] == "hello"
    assert result["type"] == 1

@pytest.mark.asyncio
async def test_param_read_body_mode_invalid_json():
    req = MagicMock()
    req.json = AsyncMock(side_effect=Exception("bad json"))
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    result = await func_request_param_read(request=req, mode="body", strict=0, config=None)
    assert result == {"body": None}

# ===========================================================================
# func_request_param_read: config validation (5-tuple format)
# ===========================================================================
@pytest.mark.asyncio
async def test_param_read_mandatory_missing():
    req = MagicMock()
    req.query_params = {}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    config = [("table", "str", 1, None, None)]
    with pytest.raises(Exception, match="parameter 'table' missing"):
        await func_request_param_read(request=req, mode="query", strict=0, config=config)

@pytest.mark.asyncio
async def test_param_read_mandatory_empty_string():
    req = MagicMock()
    req.query_params = {"table": "   "}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    config = [("table", "str", 1, None, None)]
    with pytest.raises(Exception, match="parameter 'table' cannot be empty"):
        await func_request_param_read(request=req, mode="query", strict=0, config=config)

@pytest.mark.asyncio
async def test_param_read_default_value():
    req = MagicMock()
    req.query_params = {}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    config = [("limit", "int", 0, None, 10)]
    result = await func_request_param_read(request=req, mode="query", strict=0, config=config)
    assert result["limit"] == 10

@pytest.mark.asyncio
async def test_param_read_type_casting_int():
    req = MagicMock()
    req.query_params = {"limit": "25"}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    config = [("limit", "int", 0, None, None)]
    result = await func_request_param_read(request=req, mode="query", strict=0, config=config)
    assert result["limit"] == 25
    assert isinstance(result["limit"], int)

@pytest.mark.asyncio
async def test_param_read_type_casting_float():
    req = MagicMock()
    req.query_params = {"price": "9.99"}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    config = [("price", "float", 0, None, None)]
    result = await func_request_param_read(request=req, mode="query", strict=0, config=config)
    assert result["price"] == 9.99

@pytest.mark.asyncio
async def test_param_read_type_casting_bool_true():
    req = MagicMock()
    req.query_params = {"flag": "true"}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    config = [("flag", "bool", 0, None, None)]
    result = await func_request_param_read(request=req, mode="query", strict=0, config=config)
    assert result["flag"] == 1

@pytest.mark.asyncio
async def test_param_read_type_casting_bool_false():
    req = MagicMock()
    req.query_params = {"flag": "no"}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    config = [("flag", "bool", 0, None, None)]
    result = await func_request_param_read(request=req, mode="query", strict=0, config=config)
    assert result["flag"] == 0

@pytest.mark.asyncio
async def test_param_read_type_casting_list():
    req = MagicMock()
    req.query_params = {"ids": "1,2,3"}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    config = [("ids", "list", 0, None, None)]
    result = await func_request_param_read(request=req, mode="query", strict=0, config=config)
    assert result["ids"] == ["1", "2", "3"]

@pytest.mark.asyncio
async def test_param_read_type_casting_list_int():
    req = MagicMock()
    req.query_params = {"ids": "1,2,3"}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    config = [("ids", "list:int", 0, None, None)]
    result = await func_request_param_read(request=req, mode="query", strict=0, config=config)
    assert result["ids"] == [1, 2, 3]

@pytest.mark.asyncio
async def test_param_read_type_casting_dict():
    req = MagicMock()
    req.query_params = {"meta": '{"key":"val"}'}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    config = [("meta", "dict", 0, None, None)]
    result = await func_request_param_read(request=req, mode="query", strict=0, config=config)
    assert result["meta"] == {"key": "val"}

@pytest.mark.asyncio
async def test_param_read_allowed_values_pass():
    req = MagicMock()
    req.query_params = {"mode": "read"}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    config = [("mode", "str", 1, ["read", "write"], None)]
    result = await func_request_param_read(request=req, mode="query", strict=0, config=config)
    assert result["mode"] == "read"

@pytest.mark.asyncio
async def test_param_read_allowed_values_fail():
    req = MagicMock()
    req.query_params = {"mode": "delete"}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    config = [("mode", "str", 1, ["read", "write"], None)]
    with pytest.raises(Exception, match="value not allowed"):
        await func_request_param_read(request=req, mode="query", strict=0, config=config)

@pytest.mark.asyncio
async def test_param_read_null_string_treated_as_none():
    req = MagicMock()
    req.query_params = {"val": "null"}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    config = [("val", "str", 0, None, "default_val")]
    result = await func_request_param_read(request=req, mode="query", strict=0, config=config)
    assert result["val"] == "default_val"

@pytest.mark.asyncio
async def test_param_read_undefined_string_treated_as_none():
    req = MagicMock()
    req.query_params = {"val": "undefined"}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    config = [("val", "str", 0, None, "fallback")]
    result = await func_request_param_read(request=req, mode="query", strict=0, config=config)
    assert result["val"] == "fallback"

@pytest.mark.asyncio
async def test_param_read_strict_mode():
    req = MagicMock()
    req.query_params = {"table": "test", "extra": "junk"}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    config = [("table", "str", 1, None, None)]
    result = await func_request_param_read(request=req, mode="query", strict=1, config=config)
    assert "table" in result
    assert "extra" not in result

@pytest.mark.asyncio
async def test_param_read_invalid_config_format():
    req = MagicMock()
    req.query_params = {}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    with pytest.raises(Exception, match="invalid configuration format"):
        await func_request_param_read(request=req, mode="query", strict=0, config=["bad"])

@pytest.mark.asyncio
async def test_param_read_short_tuple():
    req = MagicMock()
    req.query_params = {}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    with pytest.raises(Exception, match="invalid config tuple length"):
        await func_request_param_read(request=req, mode="query", strict=0, config=[("key", "str")])

@pytest.mark.asyncio
async def test_param_read_invalid_dtype():
    req = MagicMock()
    req.query_params = {"x": "1"}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    with pytest.raises(Exception, match="invalid dtype"):
        await func_request_param_read(request=req, mode="query", strict=0, config=[("x", "invalid", 0, None, None)])

@pytest.mark.asyncio
async def test_param_read_mandatory_with_default_error():
    req = MagicMock()
    req.query_params = {}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    with pytest.raises(Exception, match="mandatory.*default_value must be None"):
        await func_request_param_read(request=req, mode="query", strict=0, config=[("x", "str", 1, None, "bad")])

@pytest.mark.asyncio
async def test_param_read_default_violates_allowed():
    req = MagicMock()
    req.query_params = {}
    req.headers = MagicMock()
    req.headers.items = MagicMock(return_value=[])
    with pytest.raises(Exception, match="violating allowed_values"):
        await func_request_param_read(request=req, mode="query", strict=0, config=[("x", "str", 0, ["a", "b"], "c")])

# ===========================================================================
# func_request_obj_list_read
# ===========================================================================
def test_obj_list_read_single_obj():
    result = func_request_obj_list_read(obj_body={"title": "hello"})
    assert result == [{"title": "hello"}]

def test_obj_list_read_with_obj_list():
    result = func_request_obj_list_read(obj_body={"obj_list": [{"a": 1}, {"a": 2}]})
    assert len(result) == 2

def test_obj_list_read_empty_obj_list():
    result = func_request_obj_list_read(obj_body={"obj_list": []})
    assert result == []

# ===========================================================================
# func_check_cache: inmemory mode
# ===========================================================================
@pytest.mark.asyncio
async def test_cache_get_miss_inmemory():
    result = await func_check_cache(
        mode="get", url_path="/public/object-read", query_params={"table": "test"},
        config_api={"/public/object-read": {"api_cache_sec": ["inmemory", 10]}},
        client_redis=None, user_id=0, response=None, cache_api_response={}
    )
    assert result is None

@pytest.mark.asyncio
async def test_cache_set_then_get_inmemory():
    cache = {}
    config = {"/public/object-read": {"api_cache_sec": ["inmemory", 60]}}
    body = b'{"status":1,"message":"cached"}'
    fake_response = Response(content=body, status_code=200, media_type="application/json")

    # Set
    result = await func_check_cache(
        mode="set", url_path="/public/object-read", query_params={"table": "test"},
        config_api=config, client_redis=None, user_id=0, response=fake_response,
        cache_api_response=cache
    )
    assert result.status_code == 200

    # Get
    cached = await func_check_cache(
        mode="get", url_path="/public/object-read", query_params={"table": "test"},
        config_api=config, client_redis=None, user_id=0, response=None,
        cache_api_response=cache
    )
    assert cached is not None
    assert cached.headers.get("x-cache") == "hit"

@pytest.mark.asyncio
async def test_cache_expired_inmemory():
    cache = {}
    config = {"/test": {"api_cache_sec": ["inmemory", 0]}}
    # Manually insert expired entry
    import gzip, base64
    compressed = base64.b64encode(gzip.compress(b'old')).decode()
    cache["cache:/test?:0"] = {"data": compressed, "expire_at": time.time() - 100}
    result = await func_check_cache(
        mode="get", url_path="/test", query_params={},
        config_api=config, client_redis=None, user_id=0, response=None,
        cache_api_response=cache
    )
    assert result is None

@pytest.mark.asyncio
async def test_cache_no_config():
    result = await func_check_cache(
        mode="get", url_path="/test", query_params={},
        config_api={}, client_redis=None, user_id=0, response=None,
        cache_api_response={}
    )
    assert result is None

@pytest.mark.asyncio
async def test_cache_invalid_mode():
    with pytest.raises(Exception, match="invalid cache mode"):
        await func_check_cache(
            mode="invalid", url_path="/test", query_params={},
            config_api={"/test": {"api_cache_sec": ["inmemory", 10]}},
            client_redis=None, user_id=0, response=None,
            cache_api_response={}
        )

@pytest.mark.asyncio
async def test_cache_user_id_isolation():
    cache = {}
    config = {"/my/profile": {"api_cache_sec": ["inmemory", 60]}}
    body1 = b'{"user": "alice"}'
    body2 = b'{"user": "bob"}'
    resp1 = Response(content=body1, status_code=200, media_type="application/json")
    resp2 = Response(content=body2, status_code=200, media_type="application/json")

    # Set for user 1
    await func_check_cache(mode="set", url_path="/my/profile", query_params={}, config_api=config, client_redis=None, user_id=1, response=resp1, cache_api_response=cache)
    # Set for user 2
    await func_check_cache(mode="set", url_path="/my/profile", query_params={}, config_api=config, client_redis=None, user_id=2, response=resp2, cache_api_response=cache)

    # Get user 1
    r1 = await func_check_cache(mode="get", url_path="/my/profile", query_params={}, config_api=config, client_redis=None, user_id=1, response=None, cache_api_response=cache)
    r2 = await func_check_cache(mode="get", url_path="/my/profile", query_params={}, config_api=config, client_redis=None, user_id=2, response=None, cache_api_response=cache)
    assert r1.body != r2.body
