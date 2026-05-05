import pytest
import time
from unittest.mock import patch
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _uid():
    """Return a short unique suffix for test isolation (last 6 digits of ms timestamp)."""
    return str(int(time.time() * 1000))[-6:]

# ---------------------------------------------------------------------------
# Signup — Username/Password
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_signup_username_password_success(client: AsyncClient, state):
    uid = _uid()
    body = {"type": 1, "username": f"su{uid}", "password": "testpass123"}
    r = await client.post("/auth/signup-username-password", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == 1
    user = data["message"]["user"]
    assert user["username"] == body["username"].strip().lower()
    assert "token" in data["message"]["token"]
    assert "token_refresh" in data["message"]["token"]
    # cleanup
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id=$1;", user["id"])

@pytest.mark.asyncio
async def test_signup_username_password_duplicate(client: AsyncClient, state):
    uid = _uid()
    body = {"type": 1, "username": f"du{uid}", "password": "testpass123"}
    r1 = await client.post("/auth/signup-username-password", json=body)
    assert r1.status_code == 200, r1.text
    user_id = r1.json()["message"]["user"]["id"]
    # duplicate signup should fail with 400
    r2 = await client.post("/auth/signup-username-password", json=body)
    assert r2.status_code == 400
    assert r2.json()["status"] == 0
    # cleanup
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id=$1;", user_id)

@pytest.mark.asyncio
async def test_signup_username_password_disabled(client: AsyncClient, state):
    original = state.config_is_enable_signup
    state.config_is_enable_signup = 0
    try:
        r = await client.post("/auth/signup-username-password", json={"type": 1, "username": f"sd{_uid()}", "password": "testpass123"})
    finally:
        state.config_is_enable_signup = original
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_signup_username_password_invalid_username(client: AsyncClient):
    r = await client.post("/auth/signup-username-password", json={"type": 1, "username": "Bad User", "password": "testpass123"})
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_signup_username_password_invalid_type(client: AsyncClient):
    body = {"type": 999, "username": "badtype1", "password": "testpass123"}
    r = await client.post("/auth/signup-username-password", json=body)
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_signup_username_password_missing_fields(client: AsyncClient):
    r = await client.post("/auth/signup-username-password", json={})
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_signup_username_password_weak_password(client: AsyncClient):
    uid = _uid()
    body = {"type": 1, "username": f"wp{uid}", "password": "short"}
    r = await client.post("/auth/signup-username-password", json=body)
    assert r.status_code == 400
    assert r.json()["status"] == 0

# ---------------------------------------------------------------------------
# Login — Username/Password
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_login_username_password_success(client: AsyncClient, state):
    uid = _uid()
    username = f"lu{uid}"
    password = "testpass123"
    # create user first
    r_signup = await client.post("/auth/signup-username-password", json={"type": 1, "username": username, "password": password})
    assert r_signup.status_code == 200, r_signup.text
    user_id = r_signup.json()["message"]["user"]["id"]
    # login
    r = await client.post("/auth/login-username-password", json={"type": 1, "username": username, "password": password})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == 1
    assert data["message"]["user"]["username"] == username
    assert "token" in data["message"]["token"]
    # cleanup
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id=$1;", user_id)

@pytest.mark.asyncio
async def test_login_username_password_wrong_password(client: AsyncClient, state):
    uid = _uid()
    username = f"lw{uid}"
    r_signup = await client.post("/auth/signup-username-password", json={"type": 1, "username": username, "password": "testpass123"})
    assert r_signup.status_code == 200, r_signup.text
    user_id = r_signup.json()["message"]["user"]["id"]
    # login with wrong password
    r = await client.post("/auth/login-username-password", json={"type": 1, "username": username, "password": "wrongpassword1"})
    assert r.status_code == 400
    assert r.json()["status"] == 0
    # cleanup
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id=$1;", user_id)

@pytest.mark.asyncio
async def test_login_username_password_invalid_type(client: AsyncClient):
    r = await client.post("/auth/login-username-password", json={"type": 999, "username": "ghost123", "password": "testpass123"})
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_login_username_password_not_found(client: AsyncClient):
    r = await client.post("/auth/login-username-password", json={"type": 1, "username": "ghost123", "password": "testpass123"})
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_login_username_password_missing_fields(client: AsyncClient):
    r = await client.post("/auth/login-username-password", json={})
    assert r.status_code == 400
    assert r.json()["status"] == 0

# ---------------------------------------------------------------------------
# Login — Email/Password
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_login_email_password_success(client: AsyncClient, state):
    uid = _uid()
    email = f"e{uid}@test.com"
    password = "testpass123"
    hashed = state.client_password_hasher.hash(password)
    async with state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch("INSERT INTO users (type, email, password) VALUES ($1, $2, $3) RETURNING *;", 1, email, hashed)
        user_id = records[0]["id"]
    r = await client.post("/auth/login-email-password", json={"type": 1, "email": email, "password": password})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == 1
    assert data["message"]["user"]["email"] == email
    assert "token" in data["message"]["token"]
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id=$1;", user_id)

@pytest.mark.asyncio
async def test_login_email_password_wrong_password(client: AsyncClient, state):
    uid = _uid()
    email = f"ew{uid}@test.com"
    hashed = state.client_password_hasher.hash("correctpass1")
    async with state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch("INSERT INTO users (type, email, password) VALUES ($1, $2, $3) RETURNING *;", 1, email, hashed)
        user_id = records[0]["id"]
    r = await client.post("/auth/login-email-password", json={"type": 1, "email": email, "password": "wrongpass123"})
    assert r.status_code == 400
    assert r.json()["status"] == 0
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id=$1;", user_id)

@pytest.mark.asyncio
async def test_login_email_password_invalid_type(client: AsyncClient):
    r = await client.post("/auth/login-email-password", json={"type": 999, "email": "ghost@nowhere.com", "password": "testpass123"})
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_login_email_password_not_found(client: AsyncClient):
    r = await client.post("/auth/login-email-password", json={"type": 1, "email": "ghost@nowhere.com", "password": "testpass123"})
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_login_email_password_missing_fields(client: AsyncClient):
    r = await client.post("/auth/login-email-password", json={})
    assert r.status_code == 400
    assert r.json()["status"] == 0

# ---------------------------------------------------------------------------
# Login — Mobile/Password
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_login_mobile_password_success(client: AsyncClient, state):
    uid = _uid()
    mobile = f"9000{uid}"
    password = "testpass123"
    hashed = state.client_password_hasher.hash(password)
    async with state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch("INSERT INTO users (type, mobile, password) VALUES ($1, $2, $3) RETURNING *;", 1, mobile, hashed)
        user_id = records[0]["id"]
    r = await client.post("/auth/login-mobile-password", json={"type": 1, "mobile": mobile, "password": password})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == 1
    assert data["message"]["user"]["mobile"] == mobile
    assert "token" in data["message"]["token"]
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id=$1;", user_id)

@pytest.mark.asyncio
async def test_login_mobile_password_wrong_password(client: AsyncClient, state):
    uid = _uid()
    mobile = f"8000{uid}"
    hashed = state.client_password_hasher.hash("correctpass1")
    async with state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch("INSERT INTO users (type, mobile, password) VALUES ($1, $2, $3) RETURNING *;", 1, mobile, hashed)
        user_id = records[0]["id"]
    r = await client.post("/auth/login-mobile-password", json={"type": 1, "mobile": mobile, "password": "wrongpass123"})
    assert r.status_code == 400
    assert r.json()["status"] == 0
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id=$1;", user_id)

@pytest.mark.asyncio
async def test_login_mobile_password_invalid_type(client: AsyncClient):
    r = await client.post("/auth/login-mobile-password", json={"type": 999, "mobile": "0000000000", "password": "testpass123"})
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_login_mobile_password_not_found(client: AsyncClient):
    r = await client.post("/auth/login-mobile-password", json={"type": 1, "mobile": "0000000000", "password": "testpass123"})
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_login_mobile_password_missing_fields(client: AsyncClient):
    r = await client.post("/auth/login-mobile-password", json={})
    assert r.status_code == 400
    assert r.json()["status"] == 0

# ---------------------------------------------------------------------------
# Login — Email/OTP (insert OTP directly into postgres)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_login_email_otp_new_user(client: AsyncClient, state):
    uid = _uid()
    email = f"o{uid}@test.com"
    otp = 123456
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("INSERT INTO otp (otp, email) VALUES ($1, $2);", otp, email)
    r = await client.post("/auth/login-email-otp", json={"type": 1, "email": email, "otp": otp})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == 1
    user = data["message"]["user"]
    assert user["email"] == email
    assert "token" in data["message"]["token"]
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id=$1;", user["id"])
        await conn.execute("DELETE FROM otp WHERE email=$1;", email)

@pytest.mark.asyncio
async def test_login_email_otp_existing_user(client: AsyncClient, state):
    uid = _uid()
    email = f"oe{uid}@test.com"
    otp = 654321
    async with state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch("INSERT INTO users (type, email) VALUES ($1, $2) RETURNING *;", 1, email)
        user_id = records[0]["id"]
        await conn.execute("INSERT INTO otp (otp, email) VALUES ($1, $2);", otp, email)
    r = await client.post("/auth/login-email-otp", json={"type": 1, "email": email, "otp": otp})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == 1
    assert data["message"]["user"]["id"] == user_id
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id=$1;", user_id)
        await conn.execute("DELETE FROM otp WHERE email=$1;", email)

@pytest.mark.asyncio
async def test_login_email_otp_wrong_code(client: AsyncClient, state):
    uid = _uid()
    email = f"ow{uid}@test.com"
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("INSERT INTO otp (otp, email) VALUES ($1, $2);", 111111, email)
    r = await client.post("/auth/login-email-otp", json={"type": 1, "email": email, "otp": 999999})
    assert r.status_code == 400
    assert r.json()["status"] == 0
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM otp WHERE email=$1;", email)

@pytest.mark.asyncio
async def test_login_email_otp_invalid_type(client: AsyncClient):
    r = await client.post("/auth/login-email-otp", json={"type": 999, "email": "nootp@test.com", "otp": 123456})
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_login_email_otp_no_otp_record(client: AsyncClient):
    r = await client.post("/auth/login-email-otp", json={"type": 1, "email": "nootp@test.com", "otp": 123456})
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_login_email_otp_missing_fields(client: AsyncClient):
    r = await client.post("/auth/login-email-otp", json={})
    assert r.status_code == 400
    assert r.json()["status"] == 0

# ---------------------------------------------------------------------------
# Login — Mobile/OTP (insert OTP directly into postgres)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_login_mobile_otp_new_user(client: AsyncClient, state):
    uid = _uid()
    mobile = f"7000{uid}"
    otp = 123456
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("INSERT INTO otp (otp, mobile) VALUES ($1, $2);", otp, mobile)
    r = await client.post("/auth/login-mobile-otp", json={"type": 1, "mobile": mobile, "otp": otp})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == 1
    user = data["message"]["user"]
    assert user["mobile"] == mobile
    assert "token" in data["message"]["token"]
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id=$1;", user["id"])
        await conn.execute("DELETE FROM otp WHERE mobile=$1;", mobile)

@pytest.mark.asyncio
async def test_login_mobile_otp_existing_user(client: AsyncClient, state):
    uid = _uid()
    mobile = f"6000{uid}"
    otp = 654321
    async with state.client_postgres_pool.acquire() as conn:
        records = await conn.fetch("INSERT INTO users (type, mobile) VALUES ($1, $2) RETURNING *;", 1, mobile)
        user_id = records[0]["id"]
        await conn.execute("INSERT INTO otp (otp, mobile) VALUES ($1, $2);", otp, mobile)
    r = await client.post("/auth/login-mobile-otp", json={"type": 1, "mobile": mobile, "otp": otp})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == 1
    assert data["message"]["user"]["id"] == user_id
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id=$1;", user_id)
        await conn.execute("DELETE FROM otp WHERE mobile=$1;", mobile)

@pytest.mark.asyncio
async def test_login_mobile_otp_wrong_code(client: AsyncClient, state):
    uid = _uid()
    mobile = f"5000{uid}"
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("INSERT INTO otp (otp, mobile) VALUES ($1, $2);", 111111, mobile)
    r = await client.post("/auth/login-mobile-otp", json={"type": 1, "mobile": mobile, "otp": 999999})
    assert r.status_code == 400
    assert r.json()["status"] == 0
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM otp WHERE mobile=$1;", mobile)

@pytest.mark.asyncio
async def test_login_mobile_otp_invalid_type(client: AsyncClient):
    r = await client.post("/auth/login-mobile-otp", json={"type": 999, "mobile": "0000000001", "otp": 123456})
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_login_mobile_otp_no_otp_record(client: AsyncClient):
    r = await client.post("/auth/login-mobile-otp", json={"type": 1, "mobile": "0000000001", "otp": 123456})
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_login_mobile_otp_missing_fields(client: AsyncClient):
    r = await client.post("/auth/login-mobile-otp", json={})
    assert r.status_code == 400
    assert r.json()["status"] == 0

# ---------------------------------------------------------------------------
# Login — Google (no real token available — test error paths)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_login_google_invalid_type(client: AsyncClient):
    r = await client.post("/auth/login-google", json={"type": 999, "google_token": "fake_token"})
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_login_google_invalid_token(client: AsyncClient):
    """Google token verification will raise — middleware catches it."""
    r = await client.post("/auth/login-google", json={"type": 1, "google_token": "invalid_garbage_token"})
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_login_google_missing_fields(client: AsyncClient):
    r = await client.post("/auth/login-google", json={})
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_login_google_none_token(client: AsyncClient):
    r = await client.post("/auth/login-google", json={"type": 1, "google_token": None})
    assert r.status_code == 400
    assert r.json()["status"] == 0

@pytest.mark.asyncio
async def test_login_google_new_user_success(client: AsyncClient, state):
    google_sub = f"google-new-{_uid()}"
    id_info = {"sub": google_sub, "email": f"{google_sub}@test.com", "name": "Google New"}
    with patch("core.router.auth.id_token.verify_oauth2_token", return_value=id_info):
        r = await client.post("/auth/login-google", json={"type": 1, "google_token": "valid_token"})
    assert r.status_code == 200, r.text
    data = r.json()
    user = data["message"]["user"]
    assert data["status"] == 1
    assert user["google_login_id"] == google_sub
    assert user["email"] == id_info["email"]
    assert "token" in data["message"]["token"]
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id=$1;", user["id"])

@pytest.mark.asyncio
async def test_login_google_existing_user_success(client: AsyncClient, state):
    google_sub = f"google-existing-{_uid()}"
    id_info = {"sub": google_sub, "email": f"{google_sub}@test.com", "name": "Google Existing"}
    with patch("core.router.auth.id_token.verify_oauth2_token", return_value=id_info):
        r1 = await client.post("/auth/login-google", json={"type": 1, "google_token": "valid_token"})
        assert r1.status_code == 200, r1.text
        user_id = r1.json()["message"]["user"]["id"]
        r2 = await client.post("/auth/login-google", json={"type": 1, "google_token": "valid_token"})
    assert r2.status_code == 200, r2.text
    assert r2.json()["message"]["user"]["id"] == user_id
    async with state.client_postgres_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id=$1;", user_id)

@pytest.mark.asyncio
async def test_login_google_verifier_returns_none(client: AsyncClient):
    with patch("core.router.auth.id_token.verify_oauth2_token", return_value=None):
        r = await client.post("/auth/login-google", json={"type": 1, "google_token": "empty_google_response"})
    assert r.status_code == 400
    assert r.json()["status"] == 0
