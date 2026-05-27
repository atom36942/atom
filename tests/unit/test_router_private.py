import sys
import time
import types
from pathlib import Path

import jwt
import orjson
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.app import app
import core.router.private as private_router


class FakeS3:
    def __init__(self):
        self.put_calls = []
        self.presigned_calls = []
        self.presigned_url_calls = []

    async def put_object(self, **kwargs):
        self.put_calls.append(kwargs)
        return {"ETag": "etag"}

    def generate_presigned_post(self, **kwargs):
        self.presigned_calls.append(kwargs)
        return {
            "url": f"https://{kwargs['Bucket']}.s3.test/{kwargs['Key']}",
            "fields": {"key": kwargs["Key"], "policy": "policy", "signature": "signature"},
        }
        
    def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):
        self.presigned_url_calls.append({"ClientMethod": ClientMethod, "Params": Params, "ExpiresIn": ExpiresIn})
        return f"https://{Params['Bucket']}.s3.test/{Params['Key']}?sig=fake"


class FakeAzureBlobClient:
    def __init__(self, *, container, blob):
        self.container = container
        self.blob = blob
        self.url = f"https://azure.test/{container}/{blob}"
        self.uploaded = []

    async def upload_blob(self, data):
        self.uploaded.append(data)
        return {"etag": "etag"}


class FakeAzureContainerClient:
    def __init__(self, *, container):
        self.container = container
        self.blobs = {}

    def get_blob_client(self, blob):
        client = FakeAzureBlobClient(container=self.container, blob=blob)
        self.blobs[blob] = client
        return client


class FakeAzureBlobService:
    def __init__(self):
        self.containers = {}

    def get_container_client(self, container):
        client = FakeAzureContainerClient(container=container)
        self.containers[container] = client
        return client


def bearer_token(app_state, user=None):
    user = user or {"id": 10, "type": 1, "role": None, "deactivated_at": None}
    payload = orjson.dumps(user, default=str).decode("utf-8")
    token = jwt.encode({"exp": int(time.time()) + 3600, "data": payload, "type": "access"}, app_state.config_token_secret_key)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def private_test_client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def private_client(private_test_client, monkeypatch):
    test_client = private_test_client
    originals = {
        "client_s3": test_client.app.state.client_s3,
        "client_azure_blob": test_client.app.state.client_azure_blob,
        "config_allowed_blob_services": test_client.app.state.config_allowed_blob_services,
        "config_blob_container_default": test_client.app.state.config_blob_container_default,
        "config_blob_limit_kb": test_client.app.state.config_blob_limit_kb,
        "config_blob_upload_limit_count": test_client.app.state.config_blob_upload_limit_count,
        "config_upload_url_expire_sec": test_client.app.state.config_upload_url_expire_sec,
        "config_preview_url_expire_sec": getattr(test_client.app.state, "config_preview_url_expire_sec", 360000),
        "config_s3_region_name": test_client.app.state.config_s3_region_name,
        "config_azure_account_name": test_client.app.state.config_azure_account_name,
        "config_azure_account_key": test_client.app.state.config_azure_account_key,
        "config_is_enable_log_api": test_client.app.state.config_is_enable_log_api,
        "func_postgres_create": test_client.app.state.func_postgres_create,
    }


    def fake_generate_blob_sas(**kwargs):
        fake_generate_blob_sas.calls.append(kwargs)
        return "fake-sas-token"

    fake_generate_blob_sas.calls = []

    def fake_generate_container_sas(**kwargs):
        fake_generate_container_sas.calls.append(kwargs)
        return "fake-container-sas"
        
    fake_generate_container_sas.calls = []

    class FakeBlobSasPermissions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            
    class FakeContainerSasPermissions:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    fake_blob_module = types.SimpleNamespace(
        generate_blob_sas=fake_generate_blob_sas,
        generate_container_sas=fake_generate_container_sas,
        BlobSasPermissions=FakeBlobSasPermissions,
        ContainerSasPermissions=FakeContainerSasPermissions,
    )
    monkeypatch.setitem(sys.modules, "azure", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "azure.storage", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "azure.storage.blob", fake_blob_module)

    test_client.app.state.client_s3 = FakeS3()
    test_client.app.state.client_azure_blob = FakeAzureBlobService()
    test_client.app.state.config_allowed_blob_services = ["s3", "azure"]
    test_client.app.state.config_blob_container_default = "default-container"
    test_client.app.state.config_blob_limit_kb = 1
    test_client.app.state.config_blob_upload_limit_count = 2
    test_client.app.state.config_upload_url_expire_sec = 60
    test_client.app.state.config_preview_url_expire_sec = 120
    test_client.app.state.config_s3_region_name = "us-test-1"
    test_client.app.state.config_azure_account_name = "acct"
    test_client.app.state.config_azure_account_key = "account-key"
    test_client.app.state.config_is_enable_log_api = 0

    async def fake_postgres_create(**kwargs):
        return [1 for _ in kwargs.get("obj_list", [])]

    test_client.app.state.func_postgres_create = fake_postgres_create
    test_client.app.state.fake_generate_blob_sas = fake_generate_blob_sas
    test_client.app.state.fake_generate_container_sas = fake_generate_container_sas
    monkeypatch.setattr(private_router, "generate_blob_sas", fake_generate_blob_sas)
    monkeypatch.setattr(private_router, "generate_container_sas", fake_generate_container_sas)
    monkeypatch.setattr(private_router, "BlobSasPermissions", FakeBlobSasPermissions)
    monkeypatch.setattr(private_router, "ContainerSasPermissions", FakeContainerSasPermissions)
    for route in test_client.app.routes:
        endpoint_globals = getattr(getattr(route, "endpoint", None), "__globals__", None)
        if endpoint_globals and endpoint_globals.get("__name__") == "core.router.private":
            monkeypatch.setitem(endpoint_globals, "generate_blob_sas", fake_generate_blob_sas)
            monkeypatch.setitem(endpoint_globals, "generate_container_sas", fake_generate_container_sas)
            monkeypatch.setitem(endpoint_globals, "BlobSasPermissions", FakeBlobSasPermissions)
            monkeypatch.setitem(endpoint_globals, "ContainerSasPermissions", FakeContainerSasPermissions)
    try:
        yield test_client
    finally:
        if hasattr(test_client.app.state, "fake_generate_blob_sas"):
            delattr(test_client.app.state, "fake_generate_blob_sas")
        if hasattr(test_client.app.state, "fake_generate_container_sas"):
            delattr(test_client.app.state, "fake_generate_container_sas")
        for key, value in originals.items():
            setattr(test_client.app.state, key, value)


def test_private_blob_upload_file_requires_auth(private_client):
    response = private_client.post(
        "/private/blob-upload-file",
        data={"service": "s3"},
        files=[("file", ("hello.txt", b"hello", "text/plain"))],
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "authorization token missing"}


def test_private_blob_upload_file_s3_uploads_file(private_client):
    response = private_client.post(
        "/private/blob-upload-file",
        headers=bearer_token(private_client.app.state),
        data={"service": "s3", "container": "uploads"},
        files=[("file", ("hello.txt", b"hello", "text/plain"))],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == 1
    assert body["message"]["hello.txt"].startswith("https://uploads.s3.amazonaws.com/")
    call = private_client.app.state.client_s3.put_calls[0]
    assert call["Bucket"] == "uploads"
    assert call["Body"] == b"hello"
    assert call["Key"].endswith(".txt")


def test_private_blob_upload_file_azure_uploads_file(private_client):
    response = private_client.post(
        "/private/blob-upload-file",
        headers=bearer_token(private_client.app.state),
        data={"service": "azure", "container": "images"},
        files=[("file", ("photo.png", b"png-data", "image/png"))],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"]["photo.png"].startswith("https://azure.test/images/")
    container = private_client.app.state.client_azure_blob.containers["images"]
    blob_client = next(iter(container.blobs.values()))
    assert blob_client.uploaded == [b"png-data"]
    assert blob_client.blob.endswith(".png")


def test_private_blob_upload_file_rejects_too_many_files(private_client):
    response = private_client.post(
        "/private/blob-upload-file",
        headers=bearer_token(private_client.app.state),
        data={"service": "s3"},
        files=[
            ("file", ("one.txt", b"1", "text/plain")),
            ("file", ("two.txt", b"2", "text/plain")),
            ("file", ("three.txt", b"3", "text/plain")),
        ],
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "maximum 2 files allowed"}


def test_private_blob_upload_file_rejects_large_file(private_client):
    response = private_client.post(
        "/private/blob-upload-file",
        headers=bearer_token(private_client.app.state),
        data={"service": "s3"},
        files=[("file", ("big.txt", b"x" * 1025, "text/plain"))],
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "file size exceeds 1kb"}


def test_private_blob_upload_url_s3_returns_presigned_fields(private_client):
    response = private_client.post(
        "/private/blob-upload-url?service=s3&count=2&container=uploads",
        headers=bearer_token(private_client.app.state),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["message"]) == 2
    assert body["message"][0]["key"].endswith(".bin")
    assert body["message"][0]["file_url"].startswith("https://uploads.s3.us-test-1.amazonaws.com/")
    call = private_client.app.state.client_s3.presigned_calls[0]
    assert call["Bucket"] == "uploads"
    assert call["ExpiresIn"] == 60
    assert call["Conditions"] == [["content-length-range", 1, 1024]]


def test_private_blob_upload_url_azure_returns_sas_urls(private_client):
    response = private_client.post(
        "/private/blob-upload-url?service=azure&count=1&container=images",
        headers=bearer_token(private_client.app.state),
    )

    assert response.status_code == 200
    item = response.json()["message"][0]
    assert item["upload_url"].startswith("https://acct.blob.core.windows.net/images/")
    assert item["upload_url"].endswith("?fake-sas-token")
    assert item["file_url"] == item["upload_url"].split("?", 1)[0]
    call = private_client.app.state.fake_generate_blob_sas.calls[0]
    assert call["account_name"] == "acct"
    assert call["account_key"] == "account-key"
    assert call["container_name"] == "images"
    assert call["blob_name"] == item["key"]
    assert call["permission"].kwargs == {"write": True, "create": True}


def test_private_blob_upload_url_rejects_too_many(private_client):
    response = private_client.post(
        "/private/blob-upload-url?service=s3&count=3",
        headers=bearer_token(private_client.app.state),
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "maximum 2 allowed"}


def test_private_blob_upload_url_rejects_service_not_allowed(private_client):
    private_client.app.state.config_allowed_blob_services = ["s3"]

    response = private_client.post(
        "/private/blob-upload-url?service=azure&count=1",
        headers=bearer_token(private_client.app.state),
    )

    assert response.status_code == 400
    assert response.json()["status"] == 0
    assert "value not allowed" in response.json()["message"]


def test_private_blob_container_sas(private_client):
    response = private_client.post(
        "/private/blob-container-sas?service=azure&container=images",
        headers=bearer_token(private_client.app.state),
    )
    
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == 1
    assert body["message"]["sas_token"] == "fake-container-sas"
    assert body["message"]["expiry_sec"] == 120
    
    call = private_client.app.state.fake_generate_container_sas.calls[0]
    assert call["container_name"] == "images"
    assert call["account_name"] == "acct"
    assert call["permission"].kwargs == {"read": True}

def test_private_blob_preview_urls_s3(private_client):
    response = private_client.post(
        "/private/blob-preview-urls",
        json={
            "service": "s3", 
            "urls": ["https://uploads.s3.amazonaws.com/folder/file.png"]
        },
        headers=bearer_token(private_client.app.state),
    )
    
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == 1
    
    original_url = "https://uploads.s3.amazonaws.com/folder/file.png"
    assert original_url in body["message"]
    assert body["message"][original_url] == "https://uploads.s3.test/folder/file.png?sig=fake"
    
    call = private_client.app.state.client_s3.presigned_url_calls[0]
    assert call["ClientMethod"] == "get_object"
    assert call["Params"] == {"Bucket": "uploads", "Key": "folder/file.png"}
    assert call["ExpiresIn"] == 120

def test_private_blob_preview_urls_azure(private_client):
    response = private_client.post(
        "/private/blob-preview-urls",
        json={
            "service": "azure", 
            "urls": ["https://acct.blob.core.windows.net/images/docs/contract.pdf"]
        },
        headers=bearer_token(private_client.app.state),
    )
    
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == 1
    
    original_url = "https://acct.blob.core.windows.net/images/docs/contract.pdf"
    assert original_url in body["message"]
    assert body["message"][original_url] == "https://acct.blob.core.windows.net/images/docs/contract.pdf?fake-sas-token"
    
    call = private_client.app.state.fake_generate_blob_sas.calls[0]
    assert call["account_name"] == "acct"
    assert call["container_name"] == "images"
    assert call["blob_name"] == "docs/contract.pdf"
    assert call["permission"].kwargs == {"read": True}
