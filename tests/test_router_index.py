import sys
from pathlib import Path

import orjson
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_index_returns_configured_html(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<html" in response.text.lower()


def test_index_returns_welcome_when_html_path_disabled(client):
    original_path = client.app.state.config_index_html_path
    client.app.state.config_index_html_path = None
    try:
        response = client.get("/")
    finally:
        client.app.state.config_index_html_path = original_path

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "welcome to atom"}


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "ok"}


def test_info_returns_routes_schema_and_mapping(client):
    response = client.get("/info")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == 1
    assert "/" in body["message"]["api_list"]
    assert "/health" in body["message"]["api_list"]
    assert "/info" in body["message"]["api_list"]
    assert "/openapi.json" in body["message"]["api_list"]
    assert isinstance(body["message"]["postgres_schema"], dict)
    assert body["message"]["postgres_schema"] == client.app.state.cache_postgres_schema
    expected_mapping = orjson.loads(orjson.dumps(client.app.state.config_column_int_mapping, option=orjson.OPT_NON_STR_KEYS))
    assert body["message"]["mapping"] == expected_mapping


def test_info_uses_inmemory_cache_on_second_request(client):
    first_response = client.get("/info")
    second_response = client.get("/info")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.headers.get("x-cache") == "hit"
    assert second_response.json() == first_response.json()


def test_openapi_json_returns_cached_openapi_spec(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    body = response.json()
    assert body == client.app.state.cache_openapi
    assert body["openapi"] == "3.0.0"
    assert body["info"]["title"] == "API Documentation"
    assert "/" in body["paths"]
    assert "/health" in body["paths"]
    assert "/info" in body["paths"]
    assert "/openapi.json" in body["paths"]


def test_openapi_blob_container_ops_includes_container_default(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    body = response.json()
    params = body["paths"]["/admin/blob-container-ops"]["post"]["parameters"]
    container = next(item for item in params if item["name"] == "container")
    assert container["in"] == "query"
    assert container["required"] is False
    assert container["schema"]["default"] == client.app.state.config_blob_container_default


def test_websocket_buffers_message(client):
    client.app.state.cache_postgres_buffer = {}
    with client.websocket_connect("/websocket") as websocket:
        websocket.send_text("hello")
        assert websocket.receive_text() == "buffered"
