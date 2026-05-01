import pytest
from tests.conftest import unique_id

# ---------------------------------------------------------------------------
# Auth guard: all admin endpoints require a valid token
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_no_token_rejected(client):
    endpoints = [
        ("GET", "/admin/sync"),
        ("GET", "/admin/object-read?table=test"),
        ("POST", "/admin/object-create?table=test"),
        ("PUT", "/admin/object-update?table=test"),
        ("POST", "/admin/ids-delete"),
        ("POST", "/admin/postgres-runner"),
    ]
    for method, url in endpoints:
        r = await getattr(client, method.lower())(url)
        assert r.status_code == 400, f"{method} {url} should reject without token"
        assert "token" in r.json()["message"].lower() or "authorization" in r.json()["message"].lower()

# ---------------------------------------------------------------------------
# GET /admin/sync
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_sync(client, admin_headers, db_available):
    r = await client.get("/admin/sync", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == 1

# ---------------------------------------------------------------------------
# POST /admin/object-create → GET /admin/object-read → POST /admin/ids-delete
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_object_create_read_delete(client, admin_headers, db_available):
    uid = unique_id()
    title = f"admin_test_{uid}"

    # Create
    r = await client.post(
        "/admin/object-create?table=test",
        json={"title": title},
        headers=admin_headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == 1
    created_ids = body["message"]
    assert isinstance(created_ids, list)
    assert len(created_ids) == 1
    obj_id = created_ids[0]

    # Read
    r = await client.get(
        f"/admin/object-read?table=test&title==,{title}",
        headers=admin_headers
    )
    assert r.status_code == 200
    rows = r.json()["message"]
    assert any(row["id"] == obj_id for row in rows)

    # Delete
    r = await client.post(
        "/admin/ids-delete",
        json={"table": "test", "ids": str(obj_id)},
        headers=admin_headers
    )
    assert r.status_code == 200

# ---------------------------------------------------------------------------
# PUT /admin/object-update
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_object_update(client, admin_headers, db_available):
    uid = unique_id()
    # Create
    r = await client.post("/admin/object-create?table=test", json={"title": f"upd_before_{uid}"}, headers=admin_headers)
    obj_id = r.json()["message"][0]

    # Update
    r = await client.put(
        "/admin/object-update?table=test",
        json={"id": obj_id, "title": f"upd_after_{uid}"},
        headers=admin_headers
    )
    assert r.status_code == 200

    # Verify
    r = await client.get(f"/admin/object-read?table=test&id==,{obj_id}", headers=admin_headers)
    rows = r.json()["message"]
    assert rows[0]["title"] == f"upd_after_{uid}"

    # Cleanup
    await client.post("/admin/ids-delete", json={"table": "test", "ids": str(obj_id)}, headers=admin_headers)

# ---------------------------------------------------------------------------
# POST /admin/postgres-runner
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_postgres_runner_read(client, admin_headers, db_available):
    r = await client.post(
        "/admin/postgres-runner",
        json={"mode": "read", "query": "SELECT 1 AS val"},
        headers=admin_headers
    )
    assert r.status_code == 200

@pytest.mark.asyncio
async def test_admin_postgres_runner_drop_blocked(client, admin_headers, db_available):
    r = await client.post(
        "/admin/postgres-runner",
        json={"mode": "write", "query": "DROP TABLE test"},
        headers=admin_headers
    )
    assert r.status_code == 400
    assert "drop" in r.json()["message"].lower()

@pytest.mark.asyncio
async def test_admin_postgres_runner_truncate_blocked(client, admin_headers, db_available):
    r = await client.post(
        "/admin/postgres-runner",
        json={"mode": "write", "query": "TRUNCATE test"},
        headers=admin_headers
    )
    assert r.status_code == 400
    assert "truncate" in r.json()["message"].lower()

@pytest.mark.asyncio
async def test_admin_postgres_runner_delete_blocked(client, admin_headers, db_available):
    r = await client.post(
        "/admin/postgres-runner",
        json={"mode": "write", "query": "DELETE FROM test"},
        headers=admin_headers
    )
    assert r.status_code == 400
    assert "delete" in r.json()["message"].lower()

# ---------------------------------------------------------------------------
# POST /admin/postgres-export
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_postgres_export(client, admin_headers, db_available):
    r = await client.post(
        "/admin/postgres-export",
        json={"query": "SELECT id, title FROM test LIMIT 5"},
        headers=admin_headers
    )
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")

# ---------------------------------------------------------------------------
# Bulk create
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_object_create_bulk(client, admin_headers, db_available):
    uid = unique_id()
    obj_list = [{"title": f"bulk_{uid}_{i}"} for i in range(5)]
    r = await client.post(
        "/admin/object-create?table=test",
        json={"obj_list": obj_list},
        headers=admin_headers
    )
    assert r.status_code == 200
    ids = r.json()["message"]
    assert len(ids) == 5

    # Cleanup
    await client.post("/admin/ids-delete", json={"table": "test", "ids": ",".join(str(i) for i in ids)}, headers=admin_headers)
