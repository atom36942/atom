import pytest
from tests.conftest import unique_id

# ---------------------------------------------------------------------------
# Auth guard: all /my/ endpoints require a valid token
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_my_no_token_rejected(client):
    endpoints = [
        ("GET", "/my/profile"),
        ("POST", "/my/token-refresh"),
        ("GET", "/my/object-read?table=test"),
        ("POST", "/my/object-create?table=test"),
        ("PUT", "/my/object-update?table=test"),
        ("POST", "/my/ids-delete"),
    ]
    for method, url in endpoints:
        r = await getattr(client, method.lower())(url)
        assert r.status_code == 400, f"{method} {url} should reject without token"

# ---------------------------------------------------------------------------
# GET /my/profile
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_my_profile(client, my_headers, db_available):
    r = await client.get("/my/profile", headers=my_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == 1
    msg = body["message"]
    assert "id" in msg
    assert "token" in msg

# ---------------------------------------------------------------------------
# POST /my/token-refresh
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_my_token_refresh(client, my_headers, db_available):
    r = await client.post("/my/token-refresh", headers=my_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == 1
    assert "token" in body["message"]

# ---------------------------------------------------------------------------
# Object CRUD: create, read, delete in allowed table
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_my_object_create_read_delete(client, my_headers, db_available):
    uid = unique_id()
    title = f"my_obj_{uid}"

    # Create
    r = await client.post(f"/my/object-create?table=test", json={"title": title}, headers=my_headers)
    assert r.status_code == 200
    ids = r.json()["message"]
    assert len(ids) == 1

    # Read
    r = await client.get(f"/my/object-read?table=test&title==,{title}", headers=my_headers)
    assert r.status_code == 200
    rows = r.json()["message"]
    assert len(rows) >= 1

    # Delete
    r = await client.post("/my/ids-delete", json={"table": "test", "ids": str(ids[0])}, headers=my_headers)
    assert r.status_code == 200

# ---------------------------------------------------------------------------
# Blocked table: "my" role cannot create in "users"
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_my_object_create_blocked_table(client, my_headers, db_available):
    r = await client.post(
        "/my/object-create?table=users",
        json={"username": "hacker"},
        headers=my_headers
    )
    assert r.status_code == 400
    assert "not allowed" in r.json()["message"]

# ---------------------------------------------------------------------------
# Blocked column: non-admin cannot write to restricted fields
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_my_object_create_blocked_column(client, my_headers, db_available):
    r = await client.post(
        "/my/object-create?table=test",
        json={"title": "test", "is_active": 1},
        headers=my_headers
    )
    assert r.status_code == 400
    assert "restricted" in r.json()["message"].lower() or "unauthorized" in r.json()["message"].lower()

# ---------------------------------------------------------------------------
# Object update
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_my_object_update(client, my_headers, admin_headers, db_available):
    uid = unique_id()
    # Create via my
    r = await client.post("/my/object-create?table=test", json={"title": f"myupd_{uid}"}, headers=my_headers)
    obj_id = r.json()["message"][0]

    # Update
    r = await client.put(
        "/my/object-update?table=test",
        json={"id": obj_id, "title": f"myupd_done_{uid}"},
        headers=my_headers
    )
    assert r.status_code == 200

    # Cleanup via admin
    await client.post("/admin/ids-delete", json={"table": "test", "ids": str(obj_id)}, headers=admin_headers)
