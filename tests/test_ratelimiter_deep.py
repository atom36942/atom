import pytest
import time
from core.function.app_check import func_check_ratelimiter

# ===========================================================================
# Inmemory mode: basic flow
# ===========================================================================
@pytest.mark.asyncio
async def test_ratelimiter_inmemory_first_request():
    cache = {}
    config = {"/test": {"api_ratelimiting_times_sec": ("inmemory", 5, 60)}}
    await func_check_ratelimiter(
        client_redis_ratelimiter=None, config_api=config,
        url_path="/test", identifier="user1", cache_ratelimiter=cache
    )
    key = "ratelimiter:/test:user1"
    assert key in cache
    assert cache[key]["count"] == 1

@pytest.mark.asyncio
async def test_ratelimiter_inmemory_increment():
    cache = {}
    config = {"/test": {"api_ratelimiting_times_sec": ("inmemory", 10, 60)}}
    for i in range(5):
        await func_check_ratelimiter(
            client_redis_ratelimiter=None, config_api=config,
            url_path="/test", identifier="user1", cache_ratelimiter=cache
        )
    assert cache["ratelimiter:/test:user1"]["count"] == 5

@pytest.mark.asyncio
async def test_ratelimiter_inmemory_exact_limit():
    cache = {}
    config = {"/test": {"api_ratelimiting_times_sec": ("inmemory", 3, 60)}}
    for _ in range(3):
        await func_check_ratelimiter(
            client_redis_ratelimiter=None, config_api=config,
            url_path="/test", identifier="user1", cache_ratelimiter=cache
        )
    with pytest.raises(Exception, match="ratelimiter exceeded"):
        await func_check_ratelimiter(
            client_redis_ratelimiter=None, config_api=config,
            url_path="/test", identifier="user1", cache_ratelimiter=cache
        )

@pytest.mark.asyncio
async def test_ratelimiter_inmemory_window_expires():
    cache = {}
    config = {"/test": {"api_ratelimiting_times_sec": ("inmemory", 2, 1)}}
    for _ in range(2):
        await func_check_ratelimiter(
            client_redis_ratelimiter=None, config_api=config,
            url_path="/test", identifier="user1", cache_ratelimiter=cache
        )
    # Manually expire
    cache["ratelimiter:/test:user1"]["expire_at"] = time.time() - 1
    # Should reset
    await func_check_ratelimiter(
        client_redis_ratelimiter=None, config_api=config,
        url_path="/test", identifier="user1", cache_ratelimiter=cache
    )
    assert cache["ratelimiter:/test:user1"]["count"] == 1

@pytest.mark.asyncio
async def test_ratelimiter_inmemory_user_isolation():
    cache = {}
    config = {"/test": {"api_ratelimiting_times_sec": ("inmemory", 2, 60)}}
    for _ in range(2):
        await func_check_ratelimiter(
            client_redis_ratelimiter=None, config_api=config,
            url_path="/test", identifier="user1", cache_ratelimiter=cache
        )
    # user2 should still be allowed
    await func_check_ratelimiter(
        client_redis_ratelimiter=None, config_api=config,
        url_path="/test", identifier="user2", cache_ratelimiter=cache
    )

@pytest.mark.asyncio
async def test_ratelimiter_inmemory_path_isolation():
    cache = {}
    config = {
        "/api1": {"api_ratelimiting_times_sec": ("inmemory", 2, 60)},
        "/api2": {"api_ratelimiting_times_sec": ("inmemory", 2, 60)},
    }
    for _ in range(2):
        await func_check_ratelimiter(
            client_redis_ratelimiter=None, config_api=config,
            url_path="/api1", identifier="user1", cache_ratelimiter=cache
        )
    # /api2 for same user should still work
    await func_check_ratelimiter(
        client_redis_ratelimiter=None, config_api=config,
        url_path="/api2", identifier="user1", cache_ratelimiter=cache
    )

# ===========================================================================
# Redis mode: client missing
# ===========================================================================
@pytest.mark.asyncio
async def test_ratelimiter_redis_no_client():
    config = {"/test": {"api_ratelimiting_times_sec": ("redis", 5, 60)}}
    with pytest.raises(Exception, match="redis client missing"):
        await func_check_ratelimiter(
            client_redis_ratelimiter=None, config_api=config,
            url_path="/test", identifier="user1", cache_ratelimiter={}
        )

# ===========================================================================
# No config
# ===========================================================================
@pytest.mark.asyncio
async def test_ratelimiter_no_config_for_path():
    result = await func_check_ratelimiter(
        client_redis_ratelimiter=None, config_api={},
        url_path="/test", identifier="user1", cache_ratelimiter={}
    )
    assert result is None

@pytest.mark.asyncio
async def test_ratelimiter_config_without_ratelimiter_key():
    result = await func_check_ratelimiter(
        client_redis_ratelimiter=None,
        config_api={"/test": {"api_cache_sec": ["inmemory", 10]}},
        url_path="/test", identifier="user1", cache_ratelimiter={}
    )
    assert result is None

# ===========================================================================
# Invalid mode
# ===========================================================================
@pytest.mark.asyncio
async def test_ratelimiter_invalid_mode():
    config = {"/test": {"api_ratelimiting_times_sec": ("invalid_mode", 5, 60)}}
    with pytest.raises(Exception, match="invalid ratelimiter mode"):
        await func_check_ratelimiter(
            client_redis_ratelimiter=None, config_api=config,
            url_path="/test", identifier="user1", cache_ratelimiter={}
        )
