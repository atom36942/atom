from core.app import app
import pytest

@pytest.mark.asyncio
async def test_config_signup_switch(integration_app):
    app = integration_app.app
    
    # 1. Disable signup in-memory
    app.state.config_is_enable_signup = 0
    
    payload = {"type": 1, "username": "switch_test", "password": "Password123!"}
    response = await integration_app.post("/auth/signup-username-password", json=payload)
    
    assert response.status_code == 400 # App correctly returns 400 for logic exceptions
    assert "disabled" in response.json()["message"].lower()
    print("\n✅ Config: Signup switch (Disabled) verified.")
    
    # 2. Re-enable signup
    app.state.config_is_enable_signup = 1
    response = await integration_app.post("/auth/signup-username-password", json=payload)
    assert response.json()["status"] == 1
    print("✅ Config: Signup switch (Enabled) verified.")

@pytest.mark.asyncio
async def test_config_api_logging_observability(integration_app, auth_client):
    app = integration_app.app
    
    # 1. Ensure logging is enabled
    app.state.config_is_enable_log_api = 1
    
    # 2. Trigger multiple API calls to fill the buffer
    # log_api has a buffer config of 10, but we only need 1 entry.
    # We must flush the buffer to persist it before querying.
    await integration_app.get("/info")
    
    # 3. Flush the buffer so buffered log_api entries are written to Postgres
    from core.config import config_regex, config_table, config_obj_list_limit, config_buffer_limit
    await app.state.func_postgres_create(
        client_postgres_pool=app.state.client_postgres_pool,
        client_postgres_conn=None,
        client_password_hasher=app.state.client_password_hasher,
        func_postgres_serialize=app.state.func_postgres_serialize,
        func_regex_check=app.state.func_regex_check,
        cache_postgres_schema=app.state.cache_postgres_schema,
        cache_postgres_buffer_create=app.state.cache_postgres_buffer_create,
        config_regex={},
        config_table=config_table,
        config_obj_list_limit=config_obj_list_limit,
        config_buffer_limit=config_buffer_limit,
        mode="flush",
        table="",
        obj_list=[],
    )
    
    # 4. Check the real log_api table
    pool = app.state.client_postgres_pool
    async with pool.acquire() as conn:
        log = await conn.fetchrow("SELECT * FROM log_api WHERE path = '/info' ORDER BY id DESC LIMIT 1")
        assert log is not None, "API log entry not found after flush — buffer may not have been flushed"
        assert log["path"] == "/info"
        print(f"✅ Observability: API Logging verified. Request time: {log['response_time_ms']}ms recorded.")

@pytest.mark.asyncio
async def test_config_traceback_sanitization(integration_app):
    app = integration_app.app
    
    # 1. Disable traceback
    app.state.config_is_enable_traceback = 0
    
    # 2. Trigger a known error (invalid table name) with mandatory params
    response = await integration_app.get("/public/object-read?table=invalid&limit=10&page=1&order=id desc")
    assert response.status_code == 400 # Invalid table should return 400
    
    # Verify the message is clean
    message = str(response.json()["message"]).lower()
    assert "core/" not in message
    assert "line" not in message
    print("✅ Security: Error traceback sanitization verified.")
