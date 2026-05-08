import pytest

@pytest.mark.asyncio
async def test_auth_duplicate_signup_protection(integration_app):
    # Tests that duplicate usernames are blocked by DB constraints
    unique_user = "duplicate_tester"
    payload = {"type": 1, "username": unique_user, "password": "Password123!"}
    
    # 0. Clean up any previous test runs
    pool = integration_app.app.state.client_postgres_pool
    await pool.execute("DELETE FROM users WHERE username = $1", unique_user)
    
    # 1. First signup - should succeed
    res1 = await integration_app.post("/auth/signup-username-password", json=payload)
    assert res1.json()["status"] == 1
    
    # 2. Second signup with SAME username - should fail
    res2 = await integration_app.post("/auth/signup-username-password", json=payload)
    assert res2.json()["status"] == 0
    assert "exists" in res2.json()["message"].lower() or "unique" in res2.json()["message"].lower()
    print("\n✅ Auth: Duplicate signup protection verified.")

@pytest.mark.asyncio
async def test_auth_email_otp_login_new_user(integration_app):
    # Tests the flow where a new email uses OTP login to create an account
    email = "new_otp_user@example.com"
    pool = integration_app.app.state.client_postgres_pool
    
    # 0. Clean up previous runs
    await pool.execute("DELETE FROM users WHERE email = $1", email)
    await pool.execute("DELETE FROM otp WHERE email = $1", email)
    
    # 1. Manually seed an OTP for this email
    # Use pool.execute for atomic acquire/release
    await pool.execute("INSERT INTO otp (email, otp) VALUES ($1, 123456)", email)
    
    # 2. Login with OTP - this should automatically INSERT the user
    payload = {"type": 1, "email": email, "otp": 123456}
    res = await integration_app.post("/auth/login-email-otp", json=payload)
    
    assert res.json()["status"] == 1
    assert res.json()["message"]["user"]["email"] == email
    print("✅ Auth: New user automatically created via OTP login verified.")
