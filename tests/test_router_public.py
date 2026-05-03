import pytest
from tests.conftest import unique_id

# ---------------------------------------------------------------------------
# POST /public/object-create (allowed table)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_public_object_create_allowed(client, admin_headers, db_available):
    uid = unique_id()
    r = await client.post("/public/object-create?table=test", json={"title": f"pub_create_{uid}"})
    assert r.status_code == 200
    ids = r.json()["message"]
    assert len(ids) == 1
    # Cleanup
    await client.post("/admin/ids-delete", json={"table": "test", "ids": str(ids[0])}, headers=admin_headers)

# ---------------------------------------------------------------------------
# POST /public/object-create (blocked table)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_public_object_create_disabled_table(client):
    r = await client.post("/public/object-create?table=users", json={"username": "hacker"})
    assert r.status_code == 400
    assert "not allowed" in r.json()["message"]

# ---------------------------------------------------------------------------
# POST /public/object-create (blocked column)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_public_object_create_disabled_column(client):
    r = await client.post("/public/object-create?table=test", json={"title": "test", "role": 1})
    assert r.status_code == 400

# ---------------------------------------------------------------------------
# GET /public/object-read
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_public_object_read(client, db_available):
    r = await client.get("/public/object-read?table=test&limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == 1
    assert isinstance(body["message"], list)

@pytest.mark.asyncio
async def test_public_object_read_disabled_table(client, state):
    """If config_table_read_enable_public is set and table is not in it, should error."""
    if not state.config_table_read_enable_public:
        pytest.skip("config_table_read_enable_public not configured")
    r = await client.get("/public/object-read?table=users")
    assert r.status_code == 400
    assert "not allowed" in r.json()["message"]

# ---------------------------------------------------------------------------
# GET /public/converter-number
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_public_converter_encode_decode(client):
    r = await client.get("/public/converter-number?datatype=int&mode=encode&x=hello")
    assert r.status_code == 200
    encoded = r.json()["message"]
    r2 = await client.get(f"/public/converter-number?datatype=int&mode=decode&x={encoded}")
    assert r2.status_code == 200
    assert r2.json()["message"] == "hello"

@pytest.mark.asyncio
async def test_public_converter_invalid_type(client):
    r = await client.get("/public/converter-number?datatype=invalid&mode=encode&x=test")
    assert r.status_code == 400

@pytest.mark.asyncio
async def test_public_converter_missing_param(client):
    r = await client.get("/public/converter-number?datatype=int&mode=encode")
    assert r.status_code == 400

# ---------------------------------------------------------------------------
# GET /public/table-tag-read
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_public_table_tag_read(client, admin_headers, db_available):
    uid = unique_id()
    # Create objects with tags
    obj_list = [{"title": f"tag_{uid}", "tag": ["alpha", "beta"]}, {"title": f"tag2_{uid}", "tag": ["alpha", "gamma"]}]
    r = await client.post("/admin/object-create?table=test&is_serialize=1", json={"obj_list": obj_list}, headers=admin_headers)
    assert r.status_code == 200
    ids = r.json()["message"]

    # Read tags
    r = await client.get("/public/table-tag-read?table=test&column=tag")
    assert r.status_code == 200
    tags = r.json()["message"]
    assert isinstance(tags, list)

    # Cleanup
    await client.post("/admin/ids-delete", json={"table": "test", "ids": ",".join(str(i) for i in ids)}, headers=admin_headers)

# ---------------------------------------------------------------------------
# POST /public/object-create (support table — also allowed)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_public_object_create_support(client, admin_headers, db_available):
    r = await client.post("/public/object-create?table=support", json={"description": "test support ticket"})
    assert r.status_code == 200
    ids = r.json()["message"]
    assert len(ids) == 1
    # Cleanup
    await client.post("/admin/ids-delete", json={"table": "support", "ids": str(ids[0])}, headers=admin_headers)
