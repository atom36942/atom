import pytest
import asyncio
from core.consumer.postgres_create import execute, setup

@pytest.mark.asyncio
async def test_background_consumer_flow_redis(integration_app, auth_client):
    # This test verifies the E2E flow: API -> Redis -> Consumer -> Postgres
    user = auth_client(user_id=888)
    app_state = integration_app.app.state
    table = "test"
    
    # 1. Setup the consumer state
    pool, cache_buf, cache_schema, hasher = await setup()
    pool = app_state.client_postgres_pool 
    
    # 2. Trigger API with 'queue=redis'
    payload = [{"title": "Background Item"}]
    res = await user.post(f"/my/object-create?table={table}&queue=redis&mode=now", json=payload)
    assert res.json()["status"] == 1
    print("\n✅ Background: Task placed in Redis queue.")
    
    # 3. Simulate the Consumer picking it up
    redis = app_state.client_redis
    task_raw = await redis.lpop("func_postgres_create")
    assert task_raw is not None
    
    import orjson
    task_data = orjson.loads(task_raw)
    
    # 4. Run the Consumer 'execute' logic
    await execute(pool, task_data, cache_buf, cache_schema, hasher)
    print("✅ Background: Consumer executed the task.")
    
    # 5. Verify it's now in Postgres
    async with pool.acquire() as conn:
        record = await conn.fetchrow("SELECT * FROM test WHERE title = 'Background Item'")
        assert record is not None
        assert record["created_by_id"] == 888
        print("✅ Background: Data verified in Postgres after consumer processing.")

@pytest.mark.asyncio
async def test_security_regex_guard(integration_app, auth_client):
    # Tests that func_regex_check blocks malicious patterns
    user = auth_client(user_id=1)
    
    # Attempt to use a title that might look like SQL injection or have forbidden chars
    payload = [{"title": "Malicious; DROP TABLE users; --"}]
    
    res = await user.post("/my/object-create?table=test&mode=now", json=payload)
    
    # If your regex works, it should return status 0 or throw an exception
    assert res.json()["status"] == 0
    assert "regex" in res.json()["message"].lower() or "invalid" in res.json()["message"].lower()
    print("✅ Security: Regex Guard blocked potentially malicious input.")
