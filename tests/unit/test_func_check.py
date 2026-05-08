import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.function import func_check

@pytest.mark.asyncio
async def test_func_check_success():
    # Mock app_routes
    route = MagicMock()
    route.path = "/public/test"
    app_routes = [route]
    
    # Mock config_api
    current_config_api = {
        "/public/test": {"id": 1}
    }
    
    # Other params
    allowed_roles = ["public"]
    api_roles_auth = ["/my/", "/admin/"]
    client_postgres_pool = AsyncMock()
    
    # We need to mock several internal helper functions or the modules they use
    # Since func_check is highly integrated, we mock the specific checks that interact with the filesystem or DB
    
    with patch("core.function.open", create=True) as mock_open:
        # Mock empty config.py and function.py to pass standard checks
        mock_open.return_value.__enter__.return_value.read.return_value = ""
        
        with patch("os.path.isfile", return_value=True), \
             patch("os.listdir", return_value=[]), \
             patch("os.path.isdir", return_value=False):
            
            # Mock asyncpg results for DB checks
            client_postgres_pool.fetch.return_value = [] # No redundant indexes
            client_postgres_pool.fetchval.return_value = 1 # Root user exists
            
            # This should pass without raising Exception
            await func_check(
                app_routes=app_routes,
                current_config_api=current_config_api,
                allowed_roles=allowed_roles,
                api_roles_auth=api_roles_auth,
                client_postgres_pool=client_postgres_pool
            )

@pytest.mark.asyncio
async def test_func_check_raises_exception_on_missing_route_in_app():
    app_routes = [] # Empty app routes
    current_config_api = {
        "/public/missing": {"id": 1}
    }
    
    with pytest.raises(Exception, match="config_api paths missing from app: /public/missing"):
        await func_check(
            app_routes=app_routes,
            current_config_api=current_config_api,
            allowed_roles=[],
            api_roles_auth=[],
            client_postgres_pool=None
        )

@pytest.mark.asyncio
async def test_func_check_raises_exception_on_missing_api_id():
    route = MagicMock()
    route.path = "/public/test"
    app_routes = [route]
    current_config_api = {
        "/public/test": {} # Missing 'id'
    }
    
    with pytest.raises(Exception, match="missing mandatory API ID for: /public/test"):
        await func_check(
            app_routes=app_routes,
            current_config_api=current_config_api,
            allowed_roles=[],
            api_roles_auth=[],
            client_postgres_pool=None
        )

@pytest.mark.asyncio
async def test_func_check_raises_exception_on_duplicate_api_id():
    r1 = MagicMock(); r1.path = "/a"
    r2 = MagicMock(); r2.path = "/b"
    app_routes = [r1, r2]
    current_config_api = {
        "/a": {"id": 1},
        "/b": {"id": 1} # Duplicate ID
    }
    
    with pytest.raises(Exception, match="duplicate API IDs in config_api: 1"):
        await func_check(
            app_routes=app_routes,
            current_config_api=current_config_api,
            allowed_roles=[],
            api_roles_auth=[],
            client_postgres_pool=None
        )

@pytest.mark.asyncio
async def test_func_check_raises_exception_on_invalid_mode():
    route = MagicMock(); route.path = "/public/test"
    app_routes = [route]
    current_config_api = {
        "/public/test": {
            "id": 1,
            "api_cache_sec": ["invalid_mode", 60]
        }
    }
    
    with pytest.raises(Exception, match="/public/test invalid api_cache_sec mode"):
        await func_check(
            app_routes=app_routes,
            current_config_api=current_config_api,
            allowed_roles=[],
            api_roles_auth=[],
            client_postgres_pool=None
        )
