import time

import jwt
import orjson
import pytest

from core.function import (
    func_api_file_to_chunks,
    func_middleware_check_auth,
    func_producer,
    func_token_encode,
)


@pytest.mark.asyncio
async def test_middleware_check_auth_decodes_bearer_token_for_protected_route():
    secret = "test-secret-with-at-least-32-bytes"
    payload = {"id": 42, "role": 1, "is_active": 1}
    token = jwt.encode({"data": orjson.dumps(payload).decode("utf-8")}, secret)

    user = await func_middleware_check_auth(
        headers={"Authorization": f"Bearer {token}"},
        url_path="/my/profile",
        config_token_secret_key=secret,
        config_api_namespace_auth=["/my/"],
    )

    assert user == payload


@pytest.mark.asyncio
async def test_middleware_check_auth_allows_public_route_without_token():
    user = await func_middleware_check_auth(
        headers={},
        url_path="/public/object-read",
        config_token_secret_key="test-secret",
        config_api_namespace_auth=["/my/", "/private/", "/admin/"],
    )

    assert user == {}


@pytest.mark.asyncio
async def test_middleware_check_auth_rejects_protected_route_without_token():
    with pytest.raises(Exception, match="authorization token missing"):
        await func_middleware_check_auth(
            headers={},
            url_path="/private/blob-upload-file",
            config_token_secret_key="test-secret",
            config_api_namespace_auth=["/private/"],
        )


@pytest.mark.asyncio
async def test_token_encode_filters_payload_and_sets_token_types():
    secret = "test-secret-with-at-least-32-bytes"
    tokens = await func_token_encode(
        user={"id": 7, "role": 1, "ignored": "nope"},
        config_token_secret_key=secret,
        config_token_expiry_sec=60,
        config_token_refresh_expiry_sec=120,
        config_token_key=["id", "role"],
    )

    access = jwt.decode(tokens["token"], secret, algorithms="HS256")
    refresh = jwt.decode(tokens["token_refresh"], secret, algorithms="HS256")

    assert orjson.loads(access["data"]) == {"id": 7, "role": 1}
    assert orjson.loads(refresh["data"]) == {"id": 7, "role": 1}
    assert access["type"] == "access"
    assert refresh["type"] == "refresh"
    assert access["exp"] >= int(time.time()) + 55
    assert refresh["exp"] >= int(time.time()) + 115


@pytest.mark.asyncio
async def test_producer_rejects_missing_or_unknown_queue():
    common = {
        "client_celery_producer": None,
        "client_kafka_producer": None,
        "client_rabbitmq_producer": None,
        "client_redis_producer": None,
        "channel": "jobs",
        "payload": {"id": 1},
    }

    with pytest.raises(Exception, match="queue missing"):
        await func_producer(queue="", **common)

    with pytest.raises(Exception, match="invalid queue"):
        await func_producer(queue="sqs", **common)


@pytest.mark.asyncio
async def test_producer_dispatches_to_redis_as_json_string():
    class FakeRedisProducer:
        def __init__(self):
            self.calls = []

        async def lpush(self, channel, payload):
            self.calls.append((channel, payload))
            return 1

    producer = FakeRedisProducer()

    result = await func_producer(
        queue="redis",
        client_celery_producer=None,
        client_kafka_producer=None,
        client_rabbitmq_producer=None,
        client_redis_producer=producer,
        channel="postgres-create",
        payload={"table": "test", "obj_list": [{"id": 1}]},
    )

    assert result == 1
    assert producer.calls == [
        ("postgres-create", '{"table":"test","obj_list":[{"id":1}]}')
    ]


@pytest.mark.asyncio
async def test_api_file_to_chunks_yields_csv_rows_in_configured_batches():
    class FakeUploadFile:
        async def read(self):
            return b"id,name\n1,Ada\n2,Grace\n3,Linus\n"

    chunks = [
        chunk
        async for chunk in func_api_file_to_chunks(
            upload_file=FakeUploadFile(),
            chunk_size=2,
        )
    ]

    assert chunks == [
        [{"id": "1", "name": "Ada"}, {"id": "2", "name": "Grace"}],
        [{"id": "3", "name": "Linus"}],
    ]
