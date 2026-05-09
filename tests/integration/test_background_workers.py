import pytest
import asyncio

@pytest.mark.asyncio
async def test_background_consumer_flow_redis(integration_app, auth_client):
    # This test verifies the E2E flow: API -> Redis pub/sub -> Consumer -> Postgres
    user = auth_client(user_id=888)
    app_state = integration_app.app.state
    table = "test"
    pool = app_state.client_postgres_pool
    
    # 1. Subscribe to the channel BEFORE the API call publishes
    redis_sub = app_state.client_redis_producer
    pubsub = redis_sub.pubsub()
    await pubsub.subscribe("func_postgres_create")
    # Consume the subscription confirmation message
    await pubsub.get_message(timeout=1)
    
    # 2. Trigger API with 'queue=redis'
    payload = {"obj_list": [{"title": "Background Item"}]}
    res = await user.post(f"/my/object-create?table={table}&queue=redis&mode=now", json=payload)
    assert res.json()["status"] == 1
    print("\n✅ Background: Task published to Redis channel.")
    
    # 3. Receive the published message
    message = await pubsub.get_message(timeout=5)
    assert message is not None and message["type"] == "message", f"No message received from pub/sub: {message}"
    
    import orjson
    task_data = orjson.loads(message["data"])
    await pubsub.unsubscribe("func_postgres_create")
    await pubsub.aclose()
    
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
