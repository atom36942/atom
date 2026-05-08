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
    
    # 2. Trigger an API call
    await integration_app.get("/info")
    
    # 3. Check the real log_api table
    pool = app.state.client_postgres_pool
    async with pool.acquire() as conn:
        # Paginating in my check as well
        log = await conn.fetchrow("SELECT * FROM log_api WHERE api = '/info' ORDER BY id DESC LIMIT 1")
        assert log is not None
        assert log["api"] == "/info"
        assert log["status"] == 200
        print(f"✅ Observability: API Logging verified. Request time: {log['time_ms']}ms recorded.")

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
