import pytest
import asyncio

@pytest.mark.asyncio
async def test_scenario_rate_limiting(integration_app):
    # SCENARIO: Verify that the Redis rate limiter blocks excessive requests
    
    # 1. Ensure the limiter is clean
    redis = integration_app.app.state.client_redis
    await redis.flushdb()
    
    # 2. Hammer the 'object-read' API (which has rate limits)
    # We need valid params to pass the validation layer first
    url = "/public/object-read?table=test&limit=10&page=1&order=id desc"
    for i in range(30):
        res = await integration_app.get(url)
        if res.status_code == 429:
            print(f"\n✅ Rate Limiter: Successfully triggered 429 after {i+1} attempts.")
            return
            
    pytest.fail(f"Rate limiter did not trigger! Last status: {res.status_code}")

@pytest.mark.asyncio
async def test_scenario_db_state_matching(integration_app, auth_client):
    # SCENARIO: Verify that API output exactly matches what's in the DB
    user = auth_client(user_id=777)
    table = "test"
    pool = integration_app.app.state.client_postgres_pool
    
    # 0. Clean up
    await pool.execute(f"DELETE FROM {table}")
    
    # 1. Create via API using the correct 'obj_list' envelope
    payload = {"obj_list": [{"title": "State Check"}]}
    res_create = await user.post(f"/my/object-create?table={table}&mode=now", json=payload)
    new_id = res_create.json()["message"][0]
    
    # 2. Read via API
    res_read = await user.get(f"/my/object-read?table={table}&id={new_id}&limit=1&page=1&order=id desc")
    api_data = res_read.json()["message"][0]
    
    # 3. Read directly from Postgres (using safe pool.fetchrow)
    db_data = await pool.fetchrow(f"SELECT * FROM {table} WHERE id = $1", new_id)
        
    # 4. Compare
    assert api_data["title"] == db_data["title"]
    assert api_data["created_by_id"] == db_data["created_by_id"]
    print("✅ Scenario: API data perfectly matches database state.")

@pytest.mark.asyncio
async def test_scenario_redis_cache_integrity(integration_app):
    # SCENARIO: Verify that Redis cache actually stores and returns data
    url = "/public/object-read?table=test&limit=10&page=1&order=id desc"
    await integration_app.get(url)
    
    # 2. Directly check REAL Redis
    redis = integration_app.app.state.client_redis
    keys = await redis.keys("*")
    assert len(keys) > 0
    print(f"✅ Scenario: Verified {len(keys)} keys stored in Redis cache.")
