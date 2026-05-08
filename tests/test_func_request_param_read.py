import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.function import func_request_param_read

class FakeRequest:
    def __init__(self, query_params=None, headers=None, json_data=None, form_data=None):
        self.query_params = query_params or {}
        self.headers = headers or {}
        self._json_data = json_data
        self._form_data = form_data

    async def json(self):
        if self._json_data is None: raise Exception("No JSON")
        return self._json_data

    async def form(self):
        if self._form_data is None: return MagicMock()
        return self._form_data

@pytest.mark.asyncio
async def test_func_request_param_read_types():
    req = FakeRequest(query_params={
        "a": "123",
        "b": "1.5",
        "c": "yes",
        "d": "a,b,c",
        "e": '{"key": "val"}',
        "f": "456"
    })
    
    config = [
        ("a", "int", 1, None, None),
        ("b", "float", 1, None, None),
        ("c", "bool", 1, None, None),
        ("d", "list", 1, None, None),
        ("e", "dict", 1, None, None),
        ("f", "str", 1, None, None),
        ("g", "int", 0, None, 999) # Default value
    ]
    
    res = await func_request_param_read(request=req, mode="query", strict=1, config=config)
    
    assert res["a"] == 123
    assert res["b"] == 1.5
    assert res["c"] == 1
    assert res["d"] == ["a", "b", "c"]
    assert res["e"] == {"key": "val"}
    assert res["f"] == "456"
    assert res["g"] == 999

@pytest.mark.asyncio
async def test_func_request_param_read_list_int():
    req = FakeRequest(query_params={"ids": "1, 2, 3"})
    config = [("ids", "list:int", 1, None, None)]
    
    res = await func_request_param_read(request=req, mode="query", strict=1, config=config)
    assert res["ids"] == [1, 2, 3]

@pytest.mark.asyncio
async def test_func_request_param_read_mandatory_missing_raises():
    req = FakeRequest(query_params={})
    config = [("missing", "int", 1, None, None)]
    
    with pytest.raises(Exception, match="parameter 'missing' missing"):
        await func_request_param_read(request=req, mode="query", strict=1, config=config)

@pytest.mark.asyncio
async def test_func_request_param_read_allowed_values():
    req = FakeRequest(query_params={"mode": "fast"})
    config = [("mode", "str", 1, ["fast", "slow"], None)]
    
    res = await func_request_param_read(request=req, mode="query", strict=1, config=config)
    assert res["mode"] == "fast"
    
    req_bad = FakeRequest(query_params={"mode": "turbo"})
    with pytest.raises(Exception, match="value not allowed"):
        await func_request_param_read(request=req_bad, mode="query", strict=1, config=config)

@pytest.mark.asyncio
async def test_func_request_param_read_header_fallback():
    req = FakeRequest(headers={"x-api-key": "secret"})
    config = [("x-api-key", "str", 1, None, None)]
    
    # Mode is query, but should fallback to header if not found in query
    res = await func_request_param_read(request=req, mode="query", strict=1, config=config)
    assert res["x-api-key"] == "secret"
