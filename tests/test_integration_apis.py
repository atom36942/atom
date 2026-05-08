import pytest

@pytest.mark.asyncio
async def test_api_signup_integration(integration_app):
    # This uses the 'integration_app' fixture from conftest.py
    # It is a real FastAPI app connected to real Docker containers!
    
    payload = {
        "email": "integration_user@example.com",
        "username": "int_user",
        "password": "Password123!",
        "type": 1
    }
    
    # 1. Call the real Signup API
    response = integration_app.post("/auth/signup", json=payload)
    
    # 2. Verify the response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == 1
    assert "success" in data["message"].lower()
    
    # 3. Prove it's in the REAL database
    # We can access the app state directly from the fixture
    pool = integration_app.app.state.client_postgres_pool
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE email = $1", payload["email"])
        assert user is not None
        assert user["username"] == payload["username"]
        print(f"\n✅ Verified: User '{user['username']}' exists in real Postgres container.")

@pytest.mark.asyncio
async def test_api_login_integration(integration_app):
    # Test the login flow after the user was created in the previous test
    # (Note: session-scoped fixtures keep the DB state between tests)
    
    payload = {
        "email": "integration_user@example.com",
        "password": "Password123!"
    }
    
    response = integration_app.post("/auth/login", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == 1
    assert "token" in data["message"]
    print("✅ Verified: Login successful with real JWT generation and DB verification.")
