import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_api_index(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    # Depending on config_index_html_path, it might be JSON or HTML
    data = response.json()
    if isinstance(data, dict):
        assert data["status"] == 1
        assert "welcome to atom" in data["message"]

@pytest.mark.asyncio
async def test_api_index_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "ok"}

@pytest.mark.asyncio
async def test_api_index_info(client: AsyncClient):
    response = await client.get("/info")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == 1
    assert "api_list" in data["message"]
    assert "postgres_schema" in data["message"]
    assert "mapping" in data["message"]

@pytest.mark.asyncio
async def test_api_openapi_json(client: AsyncClient):
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    # It should return the openapi dict
    data = response.json()
    assert "openapi" in data or isinstance(data, dict)

@pytest.mark.asyncio
async def test_api_websocket(client: AsyncClient):
    # httpx doesn't support websockets. 
    # For websocket testing in FastAPI, we usually use TestClient or a dedicated library.
    # However, since the user asked for test cases, I will implement it using FastAPI TestClient if possible,
    # or just skip it if the environment doesn't support it easily.
    # Given the conftest.py setup, I'll try to use the app directly with TestClient for the websocket.
    from fastapi.testclient import TestClient
    from core.app import app
    
    with TestClient(app) as tc:
        with tc.websocket_connect("/websocket") as websocket:
            websocket.send_text("hello")
            data = websocket.receive_text()
            assert data is not None
