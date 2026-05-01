import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# ---------------------------------------------------------------------------
# Middleware / Router Logic Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_admin_wrong_role_logic():
    from core.function.app_router import func_check_admin
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    
    # Mock user exists with role 99
    mock_conn.fetch.return_value = [{"role": 99}]
    
    config_api = {"/admin/sync": {"user_role_check": ["realtime", [1]]}}
    
    with pytest.raises(Exception, match="access denied"):
        await func_check_admin(
            user_dict={"id": 2, "role": 99},
            url_path="/admin/sync",
            config_api=config_api,
            client_postgres_pool=mock_pool,
            client_redis=None,
            cache_users_role={},
            config_redis_cache_ttl_sec=60
        )

@pytest.mark.asyncio
async def test_login_wrong_password_logic():
    from core.function.user import func_auth_login_username_password
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    
    mock_conn.fetch.return_value = [{"username": "test", "password": "hashed_password"}]
    mock_hasher = MagicMock()
    mock_hasher.verify.side_effect = Exception("wrong")
    
    with pytest.raises(Exception, match="incorrect password"):
        await func_auth_login_username_password(
            client_postgres_pool=mock_pool,
            client_password_hasher=mock_hasher,
            type=1,
            username="test",
            password="wrong"
        )

@pytest.mark.asyncio
async def test_login_nonexistent_user_logic():
    from core.function.user import func_auth_login_username_password
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    
    mock_conn.fetch.return_value = []
    
    with pytest.raises(Exception, match="username not found"):
        await func_auth_login_username_password(
            client_postgres_pool=mock_pool,
            client_password_hasher=MagicMock(),
            type=1,
            username="missing",
            password="any"
        )
