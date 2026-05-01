import pytest

# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_index_welcome(client):
    r = await client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == 1

# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == 1
    assert body["message"] == "ok"

# ---------------------------------------------------------------------------
# GET /info
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_info(client):
    r = await client.get("/info")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == 1
    msg = body["message"]
    assert "api_list" in msg
    assert "postgres_schema" in msg
    assert isinstance(msg["api_list"], list)
    assert len(msg["api_list"]) > 0

# ---------------------------------------------------------------------------
# GET /openapi.json
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_openapi_json(client):
    r = await client.get("/openapi.json")
    assert r.status_code == 200
    body = r.json()
    assert "openapi" in body
    assert "paths" in body
    assert len(body["paths"]) > 0
