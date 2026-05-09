import pytest

@pytest.mark.asyncio
async def test_otp_verification_lifecycle(integration_app, auth_client):
    # This tests the standard OTP creation/verification flow
    email = "otp_test@example.com"
    pool = integration_app.app.state.client_postgres_pool
    
    # 1. Seed OTP directly (matches core schema: otp, email, mobile, created_at)
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM otp WHERE email = $1", email)
        await conn.execute("INSERT INTO otp (email, otp) VALUES ($1, 999888)", email)
    
    # 2. Verify the OTP exists via direct DB query (not /my/ which filters by created_by_id)
    async with pool.acquire() as conn:
        otp_row = await conn.fetchrow("SELECT * FROM otp WHERE email = $1 AND otp = 999888", email)
    assert otp_row is not None, "OTP not found in database after seeding"
    assert otp_row["email"] == email
    print("\n✅ OTP: Seeded and verified in database.")
    
    # 3. Use the real production path: /auth/login-email-otp
    # This verifies the OTP and creates/finds the user in one step
    payload = {"type": 1, "email": email, "otp": 999888}
    res_login = await integration_app.post("/auth/login-email-otp", json=payload)
    assert res_login.status_code == 200, f"Login failed: {res_login.text}"
    assert res_login.json()["status"] == 1
    assert res_login.json()["message"]["user"]["email"] == email
    print("✅ OTP: Login successful using seeded OTP.")
    # 4. Verify the user was created in the database
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)
    assert user is not None, "User was not created after OTP login"
    assert user["email"] == email
    print("✅ OTP: User created in database after OTP login.")
