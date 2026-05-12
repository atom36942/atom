import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.app import app


@pytest.fixture(scope="module")
def middleware_test_client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def middleware_client(middleware_test_client):
    test_client = middleware_test_client
    originals = {
        "config_is_enable_log_api": test_client.app.state.config_is_enable_log_api,
        "cache_api_response": test_client.app.state.cache_api_response,
        "cache_postgres_table_list": test_client.app.state.cache_postgres_table_list,
        "config_table_read_enable_public": test_client.app.state.config_table_read_enable_public,
        "func_postgres_create": test_client.app.state.func_postgres_create,
        "func_postgres_read": test_client.app.state.func_postgres_read,
    }


    test_client.app.state.config_is_enable_log_api = 0
    test_client.app.state.cache_api_response = {}
    test_client.app.state.cache_postgres_table_list = ["test", "post"]
    test_client.app.state.config_table_read_enable_public = ["test", "post"]
    try:
        yield test_client
    finally:
        for key, value in originals.items():
            setattr(test_client.app.state, key, value)


def test_middleware_runs_api_normally_without_background_query(middleware_client):
    calls = []

    async def fake_create(**kwargs):
        calls.append(kwargs)
        return ["created-now"]

    middleware_client.app.state.func_postgres_create = fake_create

    response = middleware_client.post(
        "/public/object-create?table=test",
        json={"title": "normal"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": ["created-now"]}
    assert len(calls) == 1
    assert calls[0]["obj_list"] == [{"title": "normal"}]


def test_middleware_background_query_returns_accepted_response_and_runs_api(middleware_client):
    calls = []

    async def fake_create(**kwargs):
        calls.append(kwargs)
        return ["created-background"]

    middleware_client.app.state.func_postgres_create = fake_create

    response = middleware_client.post(
        "/public/object-create?table=test&is_background=1",
        json={"title": "background"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "added in background"}
    assert len(calls) == 1
    assert calls[0]["table"] == "test"
    assert calls[0]["obj_list"] == [{"title": "background"}]


def test_middleware_background_query_does_not_skip_authentication(middleware_client):
    calls = []

    async def fake_create(**kwargs):
        calls.append(kwargs)
        return ["should-not-run"]

    middleware_client.app.state.func_postgres_create = fake_create

    response = middleware_client.post(
        "/my/object-create?table=test&is_background=1",
        json={"title": "blocked"},
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "authorization token missing"}
    assert calls == []


def test_middleware_background_query_takes_precedence_over_cache(middleware_client):
    calls = []

    async def fake_read(**kwargs):
        calls.append(kwargs)
        return [{"id": len(calls)}]

    middleware_client.app.state.func_postgres_read = fake_read

    first_response = middleware_client.get("/public/object-read?table=test")
    second_response = middleware_client.get("/public/object-read?table=test")
    background_response = middleware_client.get("/public/object-read?table=test&is_background=1")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.headers.get("x-cache") == "hit"
    assert background_response.status_code == 200
    assert background_response.headers.get("x-cache") is None
    assert background_response.json() == {"status": 1, "message": "added in background"}
    assert len(calls) == 2
    assert calls[0]["table"] == "test"
    assert calls[1]["table"] == "test"
