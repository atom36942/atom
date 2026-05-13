import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock
import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.function import func_middleware_api_response_error

@pytest.mark.asyncio
async def test_error_handler_unique_violation():
    # Mock UniqueViolationError
    exc = asyncpg.exceptions.UniqueViolationError()
    exc.detail = "Key (email)=(test@example.com) already exists."
    
    msg, resp = await func_middleware_api_response_error(exception=exc, is_traceback=0, sentry_dsn=None)
    
    assert "email already exists" in msg
    assert resp.status_code == 400
    import orjson
    assert orjson.loads(resp.body)["status"] == 0

@pytest.mark.asyncio
async def test_error_handler_not_null_violation():
    exc = asyncpg.exceptions.NotNullViolationError()
    # asyncpg errors often have message or detail
    # In func_middleware_api_response_error it looks for "message"
    exc.message = 'null value in column "username" of relation "users" violates not-null constraint'
    
    msg, resp = await func_middleware_api_response_error(exception=exc, is_traceback=0, sentry_dsn=None)
    
    assert "username required" in msg # Matches current code behavior (column[0])
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_error_handler_generic_exception():
    exc = Exception("something went wrong")
    
    msg, resp = await func_middleware_api_response_error(exception=exc, is_traceback=0, sentry_dsn=None)
    
    assert msg == "something went wrong"
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_error_handler_sentry_capture():
    exc = Exception("sentry test")
    with patch("sentry_sdk.capture_exception") as mock_capture:
        # We need to ensure sentry_sdk is imported in the test environment or mock it
        with patch.dict("sys.modules", {"sentry_sdk": MagicMock()}):
            import sentry_sdk
            await func_middleware_api_response_error(exception=exc, is_traceback=0, sentry_dsn="http://dsn")
            sentry_sdk.capture_exception.assert_called_once_with(exc)

from unittest.mock import patch
