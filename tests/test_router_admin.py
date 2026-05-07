import sys
import time
from pathlib import Path

import jwt
import orjson
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.app import app


class FakeMongoCollection:
    def __init__(self):
        self.inserted = []
        self.updated = []
        self.deleted = []

    async def insert_many(self, obj_list):
        self.inserted.extend(obj_list)

    async def update_one(self, query, update):
        self.updated.append((query, update))

    async def delete_many(self, query):
        self.deleted.append(query)


class FakeMongoDatabase:
    def __init__(self, collection):
        self.collection = collection

    def __getitem__(self, _name):
        return self.collection


class FakeMongo:
    def __init__(self):
        self.collection = FakeMongoCollection()

    def __getitem__(self, _name):
        return FakeMongoDatabase(self.collection)


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePostgresPool:
    def __init__(self):
        self.conn = FakePostgresConn()

    def acquire(self):
        return FakeAcquire(self.conn)


class FakePostgresConn:
    def __init__(self):
        self.fetch_rows = [{"id": 1, "title": "one"}]
        self.cursor_rows = []
        self.executed = []
        self.fetched_sql = []

    async def fetch(self, sql, *args, **kwargs):
        self.fetched_sql.append((sql, args, kwargs))
        normalized = " ".join(sql.lower().split())
        if "select role from users where id=$1" in normalized:
            return [{"role": 1}]
        if "select id,is_active from users where id=$1" in normalized:
            return [{"id": args[0], "is_active": 1}]
        return self.fetch_rows

    async def execute(self, sql, *args, **kwargs):
        self.executed.append((sql, args, kwargs))
        return "UPDATE 1"

    def transaction(self):
        return FakeTransaction()

    async def cursor(self, _sql):
        for row in self.cursor_rows:
            yield row


class FakeRedisPipeline:
    def __init__(self, client):
        self.client = client
        self.operations = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def setex(self, key, ttl, value):
        self.operations.append(("setex", key, ttl, value))

    def set(self, key, value):
        self.operations.append(("set", key, value))

    def delete(self, key):
        self.operations.append(("delete", key))

    async def execute(self):
        self.client.pipeline_calls.append(self.operations)
        return "OK"


class FakeRedis:
    def __init__(self):
        self.pipeline_calls = []

    def pipeline(self, transaction=True):
        self.transaction = transaction
        return FakeRedisPipeline(self)


class FakeS3Admin:
    def __init__(self):
        self.delete_calls = []

    async def delete_objects(self, **kwargs):
        self.delete_calls.append(kwargs)
        return {"Deleted": kwargs["Delete"]["Objects"]}


def bearer_token(app_state):
    payload = orjson.dumps({"id": 10, "type": 1, "role": 1, "is_active": 1}, default=str).decode("utf-8")
    token = jwt.encode({"exp": int(time.time()) + 3600, "data": payload, "type": "access"}, app_state.config_token_secret_key)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def admin_test_client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_client(admin_test_client):
    test_client = admin_test_client
    originals = {
        "cache_postgres_table_list": test_client.app.state.cache_postgres_table_list,
        "cache_users_role": test_client.app.state.cache_users_role,
        "client_postgres_pool": test_client.app.state.client_postgres_pool,
        "client_redis": test_client.app.state.client_redis,
        "client_s3": test_client.app.state.client_s3,
        "client_mongodb": test_client.app.state.client_mongodb,
        "config_is_enable_log_api": test_client.app.state.config_is_enable_log_api,
        "config_is_enable_traceback": test_client.app.state.config_is_enable_traceback,
        "config_redis_cache_ttl_sec": test_client.app.state.config_redis_cache_ttl_sec,
        "config_obj_list_limit": test_client.app.state.config_obj_list_limit,
        "config_is_enable_otp_users_update_admin": test_client.app.state.config_is_enable_otp_users_update_admin,
        "func_middleware_api_log_create": test_client.app.state.func_middleware_api_log_create,
        "func_postgres_create": test_client.app.state.func_postgres_create,
        "func_postgres_update": test_client.app.state.func_postgres_update,
        "func_otp_verify": test_client.app.state.func_otp_verify,
    }

    async def noop_api_log_create(**_kwargs):
        return None

    test_client.app.state.cache_postgres_table_list = ["test", "users"]
    test_client.app.state.cache_users_role = {10: 1}
    test_client.app.state.client_postgres_pool = FakePostgresPool()
    test_client.app.state.client_redis = FakeRedis()
    test_client.app.state.client_s3 = FakeS3Admin()
    test_client.app.state.client_mongodb = FakeMongo()
    test_client.app.state.config_is_enable_log_api = 0
    test_client.app.state.config_is_enable_traceback = 0
    test_client.app.state.config_redis_cache_ttl_sec = 60
    test_client.app.state.func_middleware_api_log_create = noop_api_log_create
    try:
        yield test_client
    finally:
        for key, value in originals.items():
            setattr(test_client.app.state, key, value)


def test_admin_mongodb_import_update_rejects_missing_id(admin_client):
    response = admin_client.post(
        "/admin/mongodb-import",
        headers=bearer_token(admin_client.app.state),
        data={"mode": "update", "database": "atom", "table": "items"},
        files={"file": ("items.csv", b"title\none\n", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "CSV format error: MongoDB update requires 'id' or '_id' column"}
    assert admin_client.app.state.client_mongodb.collection.updated == []


def test_admin_mongodb_import_delete_rejects_empty_id(admin_client):
    response = admin_client.post(
        "/admin/mongodb-import",
        headers=bearer_token(admin_client.app.state),
        data={"mode": "delete", "database": "atom", "table": "items"},
        files={"file": ("items.csv", b"id,title\n,one\n", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "CSV format error: MongoDB delete requires non-empty 'id' or '_id'"}
    assert admin_client.app.state.client_mongodb.collection.deleted == []


def test_admin_mongodb_import_update_accepts_id_or_object_id(admin_client):
    response = admin_client.post(
        "/admin/mongodb-import",
        headers=bearer_token(admin_client.app.state),
        data={"mode": "update", "database": "atom", "table": "items"},
        files={"file": ("items.csv", b"id,_id,title\n1,,one\n,2,two\n", "text/csv")},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "2 rows processed"}
    assert admin_client.app.state.client_mongodb.collection.updated == [
        ({"_id": "1"}, {"$set": {"title": "one"}}),
        ({"_id": "2"}, {"$set": {"title": "two"}}),
    ]


def test_admin_object_create_passes_admin_scope_to_postgres_create(admin_client):
    calls = {}

    async def fake_create(**kwargs):
        calls.update(kwargs)
        return [101, 102]

    admin_client.app.state.func_postgres_create = fake_create

    response = admin_client.post(
        "/admin/object-create?table=test&mode=buffer&is_serialize=1",
        headers=bearer_token(admin_client.app.state),
        json={"obj_list": [{"title": "one"}, {"title": "two"}]},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": [101, 102]}
    assert calls["table"] == "test"
    assert calls["mode"] == "buffer"
    assert calls["is_serialize"] == 1
    assert calls["obj_list"] == [{"title": "one", "updated_by_id": 10}, {"title": "two", "updated_by_id": 10}]


def test_admin_object_create_allows_restricted_field(admin_client):
    calls = {}

    async def fake_create(**kwargs):
        calls.update(kwargs)
        return [1]

    admin_client.app.state.func_postgres_create = fake_create

    response = admin_client.post(
        "/admin/object-create?table=test",
        headers=bearer_token(admin_client.app.state),
        json={"is_active": 1},
    )

    assert response.status_code == 200
    assert calls["obj_list"] == [{"is_active": 1, "updated_by_id": 10}]


def test_admin_object_update_verifies_otp_for_user_email_when_enabled(admin_client):
    otp_calls = {}
    update_calls = {}

    async def fake_otp(**kwargs):
        otp_calls.update(kwargs)
        return None

    async def fake_update(**kwargs):
        update_calls.update(kwargs)
        return "updated"

    admin_client.app.state.config_is_enable_otp_users_update_admin = 1
    admin_client.app.state.func_otp_verify = fake_otp
    admin_client.app.state.func_postgres_update = fake_update

    response = admin_client.put(
        "/admin/object-update?table=users&otp=123456",
        headers=bearer_token(admin_client.app.state),
        json={"id": 10, "email": "new@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "updated"}
    assert otp_calls["otp"] == 123456
    assert otp_calls["email"] == "new@example.com"
    assert update_calls["obj_list"] == [{"id": 10, "email": "new@example.com", "updated_by_id": 10}]


def test_admin_postgres_runner_rejects_forbidden_keywords(admin_client):
    response = admin_client.post(
        "/admin/postgres-runner",
        headers=bearer_token(admin_client.app.state),
        json={"mode": "read", "sql": "DELETE FROM test"},
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "forbidden keyword in sql"}


def test_admin_postgres_runner_read_returns_rows(admin_client):
    admin_client.app.state.client_postgres_pool.conn.fetch_rows = [{"id": 1, "title": "one"}]

    response = admin_client.post(
        "/admin/postgres-runner",
        headers=bearer_token(admin_client.app.state),
        json={"mode": "read", "sql": "select id, title from test"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": [{"id": 1, "title": "one"}]}


def test_admin_postgres_export_rejects_mutating_sql(admin_client):
    response = admin_client.post(
        "/admin/postgres-export?sql=update%20test%20set%20title='x'",
        headers=bearer_token(admin_client.app.state),
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "export restricted to select/with/explain/show/describe"}


def test_admin_postgres_export_streams_csv(admin_client):
    admin_client.app.state.client_postgres_pool.conn.cursor_rows = [
        {"id": 1, "title": 'one "quoted"'},
        {"id": 2, "title": None},
    ]

    response = admin_client.post(
        "/admin/postgres-export?sql=select%20id,title%20from%20test",
        headers=bearer_token(admin_client.app.state),
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == "attachment; filename=postgres_export.csv"
    assert response.text == 'id,title\n"1","one ""quoted"""\n"2",\n'


def test_admin_redis_import_create_validates_required_columns(admin_client):
    response = admin_client.post(
        "/admin/redis-import",
        headers=bearer_token(admin_client.app.state),
        data={"mode": "create"},
        files={"file": ("redis.csv", b"key\ncache:1\n", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "CSV format error: requires 'key' and 'value'"}
    assert admin_client.app.state.client_redis.pipeline_calls == []


def test_admin_redis_import_delete_removes_keys(admin_client):
    response = admin_client.post(
        "/admin/redis-import",
        headers=bearer_token(admin_client.app.state),
        data={"mode": "delete"},
        files={"file": ("redis.csv", b"key\ncache:1\ncache:2\n", "text/csv")},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "2 rows processed"}
    assert admin_client.app.state.client_redis.pipeline_calls == [
        [("delete", "cache:1"), ("delete", "cache:2")]
    ]


def test_admin_blob_url_delete_batches_s3_urls_by_bucket(admin_client):
    urls = [
        "https://alpha.s3.amazonaws.com/a.txt",
        "https://alpha.s3.amazonaws.com/folder/b.txt",
        "https://beta.s3.amazonaws.com/c.txt",
    ]

    response = admin_client.post(
        "/admin/blob-url-delete",
        headers=bearer_token(admin_client.app.state),
        json={"service": "s3", "url": urls},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "3 s3 URLs processed"}
    assert admin_client.app.state.client_s3.delete_calls == [
        {"Bucket": "alpha", "Delete": {"Objects": [{"Key": "a.txt"}, {"Key": "folder/b.txt"}]}},
        {"Bucket": "beta", "Delete": {"Objects": [{"Key": "c.txt"}]}},
    ]
