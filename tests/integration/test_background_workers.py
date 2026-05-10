import pytest
import asyncio

@pytest.mark.asyncio
async def test_background_consumer_flow_redis(integration_app, auth_client):
    # This test verifies the E2E flow: API -> Redis pub/sub -> Consumer -> Postgres
    user = auth_client(user_id=888)
    app_state = integration_app.app.state
    table = "test"
    pool = app_state.client_postgres_pool
    
    # 1. Clear any existing items in the queue
    redis_client = app_state.client_redis_producer
    await redis_client.delete("func_postgres_create")
    
    # 2. Trigger API with 'queue=redis'
    payload = {"obj_list": [{"title": "Background Item"}]}
    res = await user.post(f"/my/object-create?table={table}&queue=redis&mode=now", json=payload)
    assert res.json()["status"] == 1
    print("\n✅ Background: Task pushed to Redis list.")
    
    # 3. Receive the pushed message from the list (FIFO)
    # We use rpop because we used lpush in the producer
    import orjson
    message = await redis_client.rpop("func_postgres_create")
    assert message is not None, "No message received from Redis list"
    task_data = orjson.loads(message)
    
    # 4. Run the Consumer 'execute' logic using test infrastructure
    from core.consumer.postgres_create import execute
    from core.function import func_postgres_schema_read
    from argon2 import PasswordHasher
    
    cache_schema = await func_postgres_schema_read(client_postgres_pool=pool)
    cache_buf = {}
    hasher = PasswordHasher()
    
    await execute(pool, task_data, cache_buf, cache_schema, hasher)
    print("✅ Background: Consumer executed the task.")
    
    # 5. Verify it's now in Postgres
    async with pool.acquire() as conn:
        record = await conn.fetchrow("SELECT * FROM test WHERE title = 'Background Item'")
        assert record is not None
        assert record["created_by_id"] == 888
        print("✅ Background: Data verified in Postgres after consumer processing.")
