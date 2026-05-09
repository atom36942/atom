import pytest

@pytest.mark.asyncio
async def test_api_signup_integration(integration_app):
    # Tests real Signup with real containers
    payload = {
        "username": "int_user",
        "password": "Password123!",
        "type": 1
    }
    
    # Clean up
    pool = integration_app.app.state.client_postgres_pool
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE username = $1", payload["username"])
    
    # 1. Call Signup
    response = await integration_app.post("/auth/signup-username-password", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == 1
    
    # 2. Verify in DB — signup stores (type, username, password), NOT email
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE username = $1", payload["username"])
    assert user is not None, "User not found by username after signup"
    assert user["username"] == payload["username"]
    print(f"\n✅ Verified: User '{user['username']}' exists in real Postgres.")

@pytest.mark.asyncio
async def test_api_login_integration(integration_app):
    # Corrected payload: expects 'username' and 'type'
    payload = {
        "username": "int_user",
        "password": "Password123!",
        "type": 1
    }
    
    response = await integration_app.post("/auth/login-username-password", json=payload)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == 1
    assert "token" in data["message"]
    print("✅ Verified: Login successful with correct credentials.")
