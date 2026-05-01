import pytest
import time
from unittest.mock import AsyncMock, patch
from core.function.app_router import func_authenticate, func_check_admin, func_check_is_active
from core.function.app_check import func_check_ratelimiter
from core.function.app_request import func_api_response_error

# ===========================================================================
# func_authenticate
# ===========================================================================
@pytest.mark.asyncio
async def test_authenticate_valid_token(state, admin_headers):
    user = await func_authenticate(
        headers=admin_headers,
        url_path="/admin/sync",
        config_token_secret_key=state.config_token_secret_key,
        config_api_roles_auth=state.config_api_roles_auth
    )
    assert user["id"] == 1
    assert user["role"] == 1

@pytest.mark.asyncio
async def test_authenticate_missing_token_protected(state):
    with pytest.raises(Exception, match="authorization token missing"):
        await func_authenticate(
            headers={},
            url_path="/my/profile",
            config_token_secret_key=state.config_token_secret_key,
            config_api_roles_auth=state.config_api_roles_auth
        )

@pytest.mark.asyncio
async def test_authenticate_missing_token_public(state):
    user = await func_authenticate(
        headers={},
        url_path="/public/object-read",
        config_token_secret_key=state.config_token_secret_key,
        config_api_roles_auth=state.config_api_roles_auth
    )
    assert user == {}

@pytest.mark.asyncio
async def test_authenticate_invalid_token(state):
    with pytest.raises(Exception):
        await func_authenticate(
            headers={"Authorization": "Bearer invalid.jwt.token"},
            url_path="/my/profile",
            config_token_secret_key=state.config_token_secret_key,
            config_api_roles_auth=state.config_api_roles_auth
        )

# ===========================================================================
# func_check_admin
# ===========================================================================
@pytest.mark.asyncio
async def test_check_admin_valid_role(state, db_available):
    """Admin with role 1 should pass."""
    await func_check_admin(
        user_dict={"id": 1, "role": 1},
        url_path="/admin/sync",
        config_api=state.config_api,
        client_postgres_pool=state.client_postgres_pool,
        client_redis=state.client_redis,
        cache_users_role=state.cache_users_role,
        config_redis_cache_ttl_sec=state.config_redis_cache_ttl_sec
    )

@pytest.mark.asyncio
async def test_check_admin_non_admin_path(state):
    """Non-admin paths should pass regardless."""
    await func_check_admin(
        user_dict={"id": 2, "role": 99},
        url_path="/my/profile",
        config_api=state.config_api,
        client_postgres_pool=state.client_postgres_pool,
        client_redis=state.client_redis,
        cache_users_role=state.cache_users_role,
        config_redis_cache_ttl_sec=state.config_redis_cache_ttl_sec
    )

# ===========================================================================
# func_check_is_active
# ===========================================================================
@pytest.mark.asyncio
async def test_check_is_active_active_user(state):
    """Active user should pass."""
    await func_check_is_active(
        user_dict={"id": 1, "is_active": 1},
        url_path="/my/profile",
        config_api=state.config_api,
        client_postgres_pool=state.client_postgres_pool,
        client_redis=state.client_redis,
        cache_users_is_active=state.cache_users_is_active,
        config_redis_cache_ttl_sec=state.config_redis_cache_ttl_sec
    )

@pytest.mark.asyncio
async def test_check_is_active_no_user(state):
    """Empty user dict should pass (public access)."""
    await func_check_is_active(
        user_dict={},
        url_path="/public/object-read",
        config_api=state.config_api,
        client_postgres_pool=state.client_postgres_pool,
        client_redis=state.client_redis,
        cache_users_is_active=state.cache_users_is_active,
        config_redis_cache_ttl_sec=state.config_redis_cache_ttl_sec
    )

# ===========================================================================
# func_check_ratelimiter (in-memory mode)
# ===========================================================================
@pytest.mark.asyncio
async def test_ratelimiter_within_limit():
    cache = {}
    config = {"/test/endpoint": {"api_ratelimiting_times_sec": ("inmemory", 5, 60)}}
    for _ in range(5):
        await func_check_ratelimiter(
            client_redis_ratelimiter=None, config_api=config,
            url_path="/test/endpoint", identifier="test_user",
            cache_ratelimiter=cache
        )

@pytest.mark.asyncio
async def test_ratelimiter_exceeded():
    cache = {}
    config = {"/test/endpoint": {"api_ratelimiting_times_sec": ("inmemory", 2, 60)}}
    for _ in range(2):
        await func_check_ratelimiter(
            client_redis_ratelimiter=None, config_api=config,
            url_path="/test/endpoint", identifier="rate_user",
            cache_ratelimiter=cache
        )
    with pytest.raises(Exception, match="ratelimiter exceeded"):
        await func_check_ratelimiter(
            client_redis_ratelimiter=None, config_api=config,
            url_path="/test/endpoint", identifier="rate_user",
            cache_ratelimiter=cache
        )

@pytest.mark.asyncio
async def test_ratelimiter_no_config():
    result = await func_check_ratelimiter(
        client_redis_ratelimiter=None, config_api={},
        url_path="/test/endpoint", identifier="x",
        cache_ratelimiter={}
    )
    assert result is None

@pytest.mark.asyncio
async def test_ratelimiter_invalid_mode():
    config = {"/test/endpoint": {"api_ratelimiting_times_sec": ("invalid", 5, 60)}}
    with pytest.raises(Exception, match="invalid ratelimiter mode"):
        await func_check_ratelimiter(
            client_redis_ratelimiter=None, config_api=config,
            url_path="/test/endpoint", identifier="x",
            cache_ratelimiter={}
        )

# ===========================================================================
# func_api_response_error
# ===========================================================================
@pytest.mark.asyncio
async def test_error_handler_unique_violation():
    import asyncpg.exceptions
    exc = asyncpg.exceptions.UniqueViolationError("duplicate key value violates unique constraint")
    exc.detail = "Key (username)=(test) already exists."
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "already exists" in msg
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_error_handler_not_null():
    import asyncpg.exceptions
    exc = asyncpg.exceptions.NotNullViolationError('null value in column "title" of relation "test" violates not-null constraint')
    exc.message = 'null value in column "title" of relation "test" violates not-null constraint'
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "required" in msg
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_error_handler_generic():
    exc = Exception("something went wrong")
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert msg == "something went wrong"
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_error_handler_check_violation():
    import asyncpg.exceptions
    exc = asyncpg.exceptions.CheckViolationError("check constraint violated")
    exc.constraint_name = "constraint_username_regex"
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "username" in msg
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_error_handler_foreign_key():
    import asyncpg.exceptions
    exc = asyncpg.exceptions.ForeignKeyViolationError("foreign key violation")
    exc.detail = "Key (user_id)=(999) is not present in table users."
    msg, resp = await func_api_response_error(exception=exc, is_traceback=0, sentry_dsn="")
    assert "reference" in msg
    assert resp.status_code == 400
