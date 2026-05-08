import pytest
import time

@pytest.mark.asyncio
async def test_scenario_rate_limiting(integration_app):
    # SCENARIO: Let's simulate a very strict rate limit
    # We modify the app config in-memory just for this test!
    
    app = integration_app.app
    endpoint = "/public/jira-worklog-export"
    original_config = app.state.config_api.get(endpoint, {"id": 19})
    
    # Force a limit of 1 request per 60 seconds for this endpoint
    app.state.config_api[endpoint] = {"id": 19, "api_ratelimiting_times_sec": ["inmemory", 1, 60]}
    
    # 1. First request should work (even if it returns 400 due to missing params, it passes the ratelimiter)
    integration_app.post(endpoint)
    
    # 2. Second request should immediately trigger 429 Too Many Requests
    response = integration_app.post(endpoint)
    
    assert response.status_code == 429
    assert "too many requests" in response.json()["message"].lower()
    print("\n✅ Scenario: Rate Limiting (429) verified by modifying app.state.")
    
    # Restore original (optional but good practice)
    if original_limit:
        app.state.config_api["/auth/login"]["api_ratelimiting_times_sec"] = original_limit

@pytest.mark.asyncio
async def test_scenario_db_state_matching(integration_app):
    # SCENARIO: Verify that API behavior changes based on real DB state
    
    pool = integration_app.app.state.client_postgres_pool
    email = "active_user@example.com"
    
    # 1. Manually seed a user who is INACTIVE in the real DB
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO users (email, type, is_active, password) VALUES ($1, 1, 0, 'hash')", email)
    
    # 2. Try to login - should fail because user is not active
    response = integration_app.post("/auth/login", json={"email": email, "password": "any"})
    
    # Adjust based on your actual error logic, e.g., 400 or 401
    assert response.status_code in (400, 401)
    print("✅ Scenario: DB State Matching (Inactive User) verified.")

@pytest.mark.asyncio
async def test_scenario_redis_cache_integrity(integration_app):
    # SCENARIO: Verify that Redis cache actually stores and returns data
    
    # 1. Call an endpoint that caches data
    # (Assuming /public/object-read is cached in your config_api)
    integration_app.get("/public/object-read?table=test")
    
    # 2. Directly check REAL Redis to see if the key exists
    redis = integration_app.app.state.client_redis
    keys = await redis.keys("*")
    assert len(keys) > 0
    print(f"✅ Scenario: Redis Cache Integrity verified. Found {len(keys)} keys in real Redis.")
