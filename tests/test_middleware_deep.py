import pytest
from core.function.app_router import func_authenticate, func_check_admin, func_check_is_active

# ===========================================================================
# func_check_admin: token mode
# ===========================================================================
@pytest.mark.asyncio
async def test_admin_token_mode_pass(state):
    """Token mode uses role from JWT payload."""
    await func_check_admin(
        user_dict={"id": 1, "role": 1},
        url_path="/admin/object-create",
        config_api={"/admin/object-create": {"user_role_check": ["token", [1]]}},
        client_postgres_pool=None, client_redis=None,
        cache_users_role={}, config_redis_cache_ttl_sec=0
    )

@pytest.mark.asyncio
async def test_admin_token_mode_denied(state):
    with pytest.raises(Exception, match="access denied"):
        await func_check_admin(
            user_dict={"id": 2, "role": 5},
            url_path="/admin/object-create",
            config_api={"/admin/object-create": {"user_role_check": ["token", [1]]}},
            client_postgres_pool=None, client_redis=None,
            cache_users_role={}, config_redis_cache_ttl_sec=0
        )

@pytest.mark.asyncio
async def test_admin_token_mode_missing_role():
    with pytest.raises(Exception, match="user role missing"):
        await func_check_admin(
            user_dict={"id": 2},
            url_path="/admin/object-create",
            config_api={"/admin/object-create": {"user_role_check": ["token", [1]]}},
            client_postgres_pool=None, client_redis=None,
            cache_users_role={}, config_redis_cache_ttl_sec=0
        )

# ===========================================================================
# func_check_admin: inmemory mode
# ===========================================================================
@pytest.mark.asyncio
async def test_admin_inmemory_mode_pass():
    await func_check_admin(
        user_dict={"id": 1, "role": 1},
        url_path="/admin/object-read",
        config_api={"/admin/object-read": {"user_role_check": ["inmemory", [1]]}},
        client_postgres_pool=None, client_redis=None,
        cache_users_role={1: 1}, config_redis_cache_ttl_sec=0
    )

@pytest.mark.asyncio
async def test_admin_inmemory_mode_denied():
    with pytest.raises(Exception, match="access denied"):
        await func_check_admin(
            user_dict={"id": 2, "role": 5},
            url_path="/admin/object-read",
            config_api={"/admin/object-read": {"user_role_check": ["inmemory", [1]]}},
            client_postgres_pool=None, client_redis=None,
            cache_users_role={2: 5}, config_redis_cache_ttl_sec=0
        )

# ===========================================================================
# func_check_admin: realtime mode (needs DB)
# ===========================================================================
@pytest.mark.asyncio
async def test_admin_realtime_mode_pass(state, db_available):
    await func_check_admin(
        user_dict={"id": 1, "role": 1},
        url_path="/admin/sync",
        config_api={"/admin/sync": {"user_role_check": ["realtime", [1]]}},
        client_postgres_pool=state.client_postgres_pool, client_redis=None,
        cache_users_role={}, config_redis_cache_ttl_sec=0
    )

@pytest.mark.asyncio
async def test_admin_realtime_mode_denied(state, db_available):
    """User 1 has role=1, but config only allows role 99."""
    with pytest.raises(Exception, match="access denied"):
        await func_check_admin(
            user_dict={"id": 1, "role": 1},
            url_path="/admin/sync",
            config_api={"/admin/sync": {"user_role_check": ["realtime", [99]]}},
            client_postgres_pool=state.client_postgres_pool, client_redis=None,
            cache_users_role={}, config_redis_cache_ttl_sec=0
        )

# ===========================================================================
# func_check_admin: invalid mode
# ===========================================================================
@pytest.mark.asyncio
async def test_admin_invalid_mode():
    with pytest.raises(Exception, match="invalid mode"):
        await func_check_admin(
            user_dict={"id": 1, "role": 1},
            url_path="/admin/sync",
            config_api={"/admin/sync": {"user_role_check": ["invalid", [1]]}},
            client_postgres_pool=None, client_redis=None,
            cache_users_role={}, config_redis_cache_ttl_sec=0
        )

# ===========================================================================
# func_check_admin: null/empty role
# ===========================================================================
@pytest.mark.asyncio
async def test_admin_role_null():
    with pytest.raises(Exception, match="user role is null"):
        await func_check_admin(
            user_dict={"id": 1, "role": None},
            url_path="/admin/sync",
            config_api={"/admin/sync": {"user_role_check": ["token", [1]]}},
            client_postgres_pool=None, client_redis=None,
            cache_users_role={}, config_redis_cache_ttl_sec=0
        )

@pytest.mark.asyncio
async def test_admin_role_string_cast():
    """Role as string should be cast to int."""
    await func_check_admin(
        user_dict={"id": 1, "role": "1"},
        url_path="/admin/sync",
        config_api={"/admin/sync": {"user_role_check": ["token", [1]]}},
        client_postgres_pool=None, client_redis=None,
        cache_users_role={}, config_redis_cache_ttl_sec=0
    )

# ===========================================================================
# func_check_is_active: token mode
# ===========================================================================
@pytest.mark.asyncio
async def test_is_active_token_mode_pass():
    await func_check_is_active(
        user_dict={"id": 1, "is_active": 1},
        url_path="/admin/ids-delete",
        config_api={"/admin/ids-delete": {"user_is_active_check": ["token", 1]}},
        client_postgres_pool=None, client_redis=None,
        cache_users_is_active={}, config_redis_cache_ttl_sec=0
    )

@pytest.mark.asyncio
async def test_is_active_token_mode_blocked():
    with pytest.raises(Exception, match="user not active"):
        await func_check_is_active(
            user_dict={"id": 1, "is_active": 0},
            url_path="/admin/ids-delete",
            config_api={"/admin/ids-delete": {"user_is_active_check": ["token", 1]}},
            client_postgres_pool=None, client_redis=None,
            cache_users_is_active={}, config_redis_cache_ttl_sec=0
        )

@pytest.mark.asyncio
async def test_is_active_token_mode_missing():
    with pytest.raises(Exception, match="missing is_active"):
        await func_check_is_active(
            user_dict={"id": 1},
            url_path="/admin/ids-delete",
            config_api={"/admin/ids-delete": {"user_is_active_check": ["token", 1]}},
            client_postgres_pool=None, client_redis=None,
            cache_users_is_active={}, config_redis_cache_ttl_sec=0
        )

# ===========================================================================
# func_check_is_active: inmemory mode
# ===========================================================================
@pytest.mark.asyncio
async def test_is_active_inmemory_mode_pass():
    await func_check_is_active(
        user_dict={"id": 1, "is_active": 1},
        url_path="/admin/ids-delete",
        config_api={"/admin/ids-delete": {"user_is_active_check": ["inmemory", 1]}},
        client_postgres_pool=None, client_redis=None,
        cache_users_is_active={1: 1}, config_redis_cache_ttl_sec=0
    )

@pytest.mark.asyncio
async def test_is_active_inmemory_mode_blocked():
    with pytest.raises(Exception, match="user not active"):
        await func_check_is_active(
            user_dict={"id": 1, "is_active": 0},
            url_path="/admin/ids-delete",
            config_api={"/admin/ids-delete": {"user_is_active_check": ["inmemory", 1]}},
            client_postgres_pool=None, client_redis=None,
            cache_users_is_active={1: 0}, config_redis_cache_ttl_sec=0
        )

# ===========================================================================
# func_check_is_active: realtime mode
# ===========================================================================
@pytest.mark.asyncio
async def test_is_active_realtime_mode(state, db_available):
    await func_check_is_active(
        user_dict={"id": 1, "is_active": 1},
        url_path="/admin/ids-delete",
        config_api={"/admin/ids-delete": {"user_is_active_check": ["realtime", 1]}},
        client_postgres_pool=state.client_postgres_pool, client_redis=None,
        cache_users_is_active={}, config_redis_cache_ttl_sec=0
    )

# ===========================================================================
# func_check_is_active: disabled flag
# ===========================================================================
@pytest.mark.asyncio
async def test_is_active_disabled():
    """active_flag=0 means skip check entirely."""
    await func_check_is_active(
        user_dict={"id": 1, "is_active": 0},
        url_path="/admin/ids-delete",
        config_api={"/admin/ids-delete": {"user_is_active_check": ["token", 0]}},
        client_postgres_pool=None, client_redis=None,
        cache_users_is_active={}, config_redis_cache_ttl_sec=0
    )

# ===========================================================================
# func_check_is_active: no config
# ===========================================================================
@pytest.mark.asyncio
async def test_is_active_no_config():
    result = await func_check_is_active(
        user_dict={"id": 1, "is_active": 0},
        url_path="/public/object-read",
        config_api={},
        client_postgres_pool=None, client_redis=None,
        cache_users_is_active={}, config_redis_cache_ttl_sec=0
    )
    assert result is None

# ===========================================================================
# func_check_is_active: invalid mode
# ===========================================================================
@pytest.mark.asyncio
async def test_is_active_invalid_mode():
    with pytest.raises(Exception, match="invalid mode"):
        await func_check_is_active(
            user_dict={"id": 1, "is_active": 1},
            url_path="/admin/ids-delete",
            config_api={"/admin/ids-delete": {"user_is_active_check": ["invalid", 1]}},
            client_postgres_pool=None, client_redis=None,
            cache_users_is_active={}, config_redis_cache_ttl_sec=0
        )

# ===========================================================================
# func_authenticate: token variants
# ===========================================================================
@pytest.mark.asyncio
async def test_authenticate_bearer_prefix_only():
    with pytest.raises(Exception):
        await func_authenticate(
            headers={"Authorization": "Bearer "},
            url_path="/my/profile",
            config_token_secret_key="test_secret",
            config_api_roles_auth=["/my/"]
        )

@pytest.mark.asyncio
async def test_authenticate_no_bearer_prefix():
    with pytest.raises(Exception, match="authorization token missing"):
        await func_authenticate(
            headers={"Authorization": "Basic abc123"},
            url_path="/my/profile",
            config_token_secret_key="test_secret",
            config_api_roles_auth=["/my/"]
        )

@pytest.mark.asyncio
async def test_authenticate_index_no_token():
    """Index/health endpoints don't need a token."""
    user = await func_authenticate(
        headers={},
        url_path="/",
        config_token_secret_key="test_secret",
        config_api_roles_auth=["/my/", "/admin/", "/private/"]
    )
    assert user == {}

@pytest.mark.asyncio
async def test_authenticate_auth_no_token():
    """Auth endpoints don't need a token."""
    user = await func_authenticate(
        headers={},
        url_path="/auth/signup",
        config_token_secret_key="test_secret",
        config_api_roles_auth=["/my/", "/admin/", "/private/"]
    )
    assert user == {}
