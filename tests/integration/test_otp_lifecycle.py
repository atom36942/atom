import pytest

@pytest.mark.asyncio
async def test_otp_verification_lifecycle(integration_app, auth_client):
    # This tests the standard OTP creation/verification flow
    # Since we can't 'read' the email, we'll check the DB directly
    admin = auth_client(role=1)
    email = "otp_test@example.com"
    
    # 1. Trigger OTP creation
    # We'll use the signup/login flow or a dedicated OTP trigger if available
    # For now, we seed it directly to test the VERIFY logic
    pool = integration_app.app.state.client_postgres_pool
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM otp WHERE email = $1", email)
        await conn.execute("INSERT INTO otp (email, otp) VALUES ($1, 999888)", email)
    
    # 2. Check /my/ object read for otp (Admin only)
    res = await admin.get("/my/object-read?table=otp&limit=10&page=1&order=id desc")
    assert res.status_code == 200, f"Read failed: {res.text}"
    assert any(row["email"] == email for row in res.json()["message"])
    print("\n✅ OTP: Seeded and verified in database.")
    
    # 3. Use it to login
    payload = {"type": 1, "email": email, "otp": 999888}
    res_login = await integration_app.post("/auth/login-email-otp", json=payload)
    assert res_login.status_code == 200, f"Login failed: {res_login.text}"
    assert res_login.json()["status"] == 1
    print("✅ OTP: Login successful using seeded OTP.")
