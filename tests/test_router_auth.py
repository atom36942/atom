import pytest
from tests.conftest import unique_id

# ---------------------------------------------------------------------------
# POST /auth/signup-username-password
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_signup_username_password(client, db_available):
    uid = unique_id()
    r = await client.post("/auth/signup-username-password", json={"type": 1, "username": f"signup_{uid}", "password": "password123"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == 1
    msg = body["message"]
    assert "user" in msg
    assert "token" in msg
    assert msg["user"]["username"] == f"signup_{uid}"

@pytest.mark.asyncio
async def test_signup_duplicate_username(client, db_available):
    uid = unique_id()
    username = f"dup_{uid}"
    r1 = await client.post("/auth/signup-username-password", json={"type": 1, "username": username, "password": "password123"})
    assert r1.status_code == 200
    r2 = await client.post("/auth/signup-username-password", json={"type": 1, "username": username, "password": "password123"})
    assert r2.status_code == 400
    assert "already exists" in r2.json()["message"]

@pytest.mark.asyncio
async def test_signup_regex_validation_bad_username(client):
    r = await client.post("/auth/signup-username-password", json={"type": 1, "username": "AB", "password": "password123"})
    assert r.status_code == 400
    assert "Username" in r.json()["message"] or "username" in r.json()["message"].lower()

@pytest.mark.asyncio
async def test_signup_regex_validation_bad_password(client):
    uid = unique_id()
    r = await client.post("/auth/signup-username-password", json={"type": 1, "username": f"regpw_{uid}", "password": "short"})
    assert r.status_code == 400
    assert "Password" in r.json()["message"] or "password" in r.json()["message"].lower()

@pytest.mark.asyncio
async def test_signup_missing_params(client):
    r = await client.post("/auth/signup-username-password", json={"type": 1})
    assert r.status_code == 400

# ---------------------------------------------------------------------------
# POST /auth/login-username-password
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_login_username_password_success(client, db_available):
    uid = unique_id()
    username = f"login_{uid}"
    await client.post("/auth/signup-username-password", json={"type": 1, "username": username, "password": "password123"})
    r = await client.post("/auth/login-username-password", json={"type": 1, "username": username, "password": "password123"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == 1
    assert body["message"]["user"]["username"] == username
    assert "token" in body["message"]

@pytest.mark.asyncio
async def test_login_missing_params(client):
    r = await client.post("/auth/login-username-password", json={"type": 1, "username": "test"})
    assert r.status_code == 400
