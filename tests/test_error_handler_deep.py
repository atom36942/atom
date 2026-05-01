import pytest
from core.function.app_request import func_api_response_error

# ===========================================================================
# asyncpg exception handlers
# ===========================================================================
@pytest.mark.asyncio
async def test_error_unique_violation():
    import asyncpg.exceptions
    exc = asyncpg.exceptions.UniqueViolationError("dup")
    exc.detail = "Key (username)=(test) already exists."
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "username already exists" in msg
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_error_unique_violation_no_detail():
    import asyncpg.exceptions
    exc = asyncpg.exceptions.UniqueViolationError("dup")
    exc.detail = None
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "duplicate value" in msg

@pytest.mark.asyncio
async def test_error_not_null_violation():
    import asyncpg.exceptions
    exc = asyncpg.exceptions.NotNullViolationError("nn")
    exc.message = 'null value in column "title" of relation "test" violates not-null constraint'
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "required" in msg

@pytest.mark.asyncio
async def test_error_not_null_violation_no_message():
    import asyncpg.exceptions
    exc = asyncpg.exceptions.NotNullViolationError("nn")
    exc.message = ""
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "missing required field" in msg

@pytest.mark.asyncio
async def test_error_check_violation():
    import asyncpg.exceptions
    exc = asyncpg.exceptions.CheckViolationError("chk")
    exc.constraint_name = "constraint_username_regex"
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "username" in msg
    assert "invalid" in msg

@pytest.mark.asyncio
async def test_error_foreign_key_violation():
    import asyncpg.exceptions
    exc = asyncpg.exceptions.ForeignKeyViolationError("fk")
    exc.detail = "Key (user_id)=(999) is not present in table users."
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "user id" in msg
    assert "reference" in msg

@pytest.mark.asyncio
async def test_error_foreign_key_no_detail():
    import asyncpg.exceptions
    exc = asyncpg.exceptions.ForeignKeyViolationError("fk")
    exc.detail = None
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "invalid reference" in msg

@pytest.mark.asyncio
async def test_error_invalid_text_representation():
    import asyncpg.exceptions
    exc = asyncpg.exceptions.InvalidTextRepresentationError("itr")
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "text format" in msg

@pytest.mark.asyncio
async def test_error_numeric_out_of_range():
    import asyncpg.exceptions
    exc = asyncpg.exceptions.NumericValueOutOfRangeError("num")
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "numeric range" in msg

@pytest.mark.asyncio
async def test_error_string_truncation():
    import asyncpg.exceptions
    exc = asyncpg.exceptions.StringDataRightTruncationError("trunc")
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "truncation" in msg

@pytest.mark.asyncio
async def test_error_deadlock():
    import asyncpg.exceptions
    exc = asyncpg.exceptions.DeadlockDetectedError("deadlock")
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "deadlock" in msg

@pytest.mark.asyncio
async def test_error_serialization():
    import asyncpg.exceptions
    exc = asyncpg.exceptions.SerializationError("ser")
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "serialization" in msg

# ===========================================================================
# Non-asyncpg exceptions
# ===========================================================================
@pytest.mark.asyncio
async def test_error_jwt():
    import jwt.exceptions
    exc = jwt.exceptions.DecodeError("jwt decode failed")
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "token invalid" in msg

@pytest.mark.asyncio
async def test_error_redis():
    import redis.exceptions
    exc = redis.exceptions.RedisError("conn refused")
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "cache service error" in msg

@pytest.mark.asyncio
async def test_error_botocore():
    import botocore.exceptions
    exc = botocore.exceptions.ClientError({"Error": {"Code": "NoSuchBucket"}}, "GetObject")
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "cloud service error" in msg
    assert "NoSuchBucket" in msg

@pytest.mark.asyncio
async def test_error_generic():
    exc = Exception("custom error message")
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert msg == "custom error message"
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_error_value_error():
    exc = ValueError("bad value")
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert msg == "bad value"
