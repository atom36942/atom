import pytest
import asyncio

@pytest.mark.asyncio
async def test_scenario_rate_limiting(integration_app):
    # SCENARIO: Verify that the Redis rate limiter blocks excessive requests
    
    # 1. Ensure the limiter is clean
    redis = integration_app.app.state.client_redis_ratelimiter
    await redis.flushdb()
    
    # 2. Hammer the 'object-read' API (which has rate limits: 10 requests / 60 sec)
    # We need valid params to pass the validation layer first
    url = "/public/object-read?table=test&limit=10&page=1&order=id desc"
    for i in range(30):
        res = await integration_app.get(url)
        # The core error handler returns 400 (not 429) for rate limiter exceptions
        if res.status_code == 400 and "ratelimiter" in res.json().get("message", "").lower():
            print(f"\n✅ Rate Limiter: Successfully triggered after {i+1} attempts.")
            return
            
    pytest.fail(f"Rate limiter did not trigger! Last status: {res.status_code}")

@pytest.mark.asyncio
async def test_scenario_db_state_matching(integration_app, auth_client):
    # SCENARIO: Verify that API output exactly matches what's in the DB
    user = auth_client(user_id=777)
    table = "test"
    pool = integration_app.app.state.client_postgres_pool
    
    # 0. Clean up
    async with pool.acquire() as conn:
        await conn.execute(f"DELETE FROM {table}")
    
    # 1. Create via API using the correct 'obj_list' envelope
    payload = {"obj_list": [{"title": "State Check"}]}
    res_create = await user.post(f"/my/object-create?table={table}&mode=now", json=payload)
    assert res_create.status_code == 200, f"Create failed: {res_create.text}"
    assert res_create.json()["status"] == 1
    new_id = res_create.json()["message"][0]
    
    # 2. Read via API — use filter format "operator,value" as required by func_postgres_read
    res_read = await user.get(f"/my/object-read", params={"table": table, "id": f"=,{new_id}", "limit": 1, "page": 1, "order": "id desc"})
    assert res_read.status_code == 200, f"Read failed: {res_read.text}"
    api_data = res_read.json()["message"]
    assert len(api_data) > 0, f"API returned no data for id={new_id}"
    api_item = api_data[0]
    
    # 3. Read directly from Postgres (using safe pool.fetchrow)
    async with pool.acquire() as conn:
        db_data = await conn.fetchrow(f"SELECT * FROM {table} WHERE id = $1", new_id)
        
    # 4. Compare
    assert api_item["title"] == db_data["title"]
    assert api_item["created_by_id"] == db_data["created_by_id"]
    print("✅ Scenario: API data perfectly matches database state.")

@pytest.mark.asyncio
async def test_scenario_redis_cache_integrity(integration_app):
    # SCENARIO: Verify that Redis cache actually stores and returns data
    # Flush rate limiter keys first to avoid interference
    await integration_app.app.state.client_redis_ratelimiter.flushdb()
    
    url = "/public/object-read?table=test&limit=10&page=1&order=id desc"
    await integration_app.get(url)
    
    # 2. Directly check REAL Redis
    redis = integration_app.app.state.client_redis
    keys = await redis.keys("*")
    assert len(keys) > 0
    print(f"✅ Scenario: Verified {len(keys)} keys stored in Redis cache.")
