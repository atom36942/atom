import sys
import time
from types import SimpleNamespace
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

    async def bulk_write(self, operations, ordered=True):
        self.bulk_write_ordered = ordered
        for operation in operations:
            if operation.__class__.__name__ == "UpdateOne":
                self.updated.append((operation._filter, operation._doc))
            elif operation.__class__.__name__ == "DeleteOne":
                self.deleted.append(operation._filter)


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
        if "select id, deactivated_at from users where id=$1" in normalized:
            return [{"id": args[0], "deactivated_at": None}]
        if "select deleted_at from users where id=$1" in normalized:
            return [{"id": args[0], "deleted_at": None}]
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

    def delete(self, *keys):
        self.operations.append(("delete", *keys))

    async def execute(self):
        self.client.pipeline_calls.append(self.operations)
        return "OK"


class FakeRedis:
    def __init__(self):
        self.pipeline_calls = []

    def pipeline(self, transaction=True):
        self.transaction = transaction
        return FakeRedisPipeline(self)

    async def aclose(self):
        pass


class FakeS3Admin:
    def __init__(self):
        self.delete_calls = []

    async def delete_objects(self, **kwargs):
        self.delete_calls.append(kwargs)
        return {"Deleted": kwargs["Delete"]["Objects"]}


class RecursiveAzureResult:
    def __init__(self):
        self.self_ref = self


class FakeAzureAdmin:
    def __init__(self):
        self.created = []
        self.deleted = []
        self.public = []
        self.blobs = ["one.png", "nested/two.png"]
        self.empty_deleted = []

    async def create_container(self, container):
        self.created.append(container)
        return RecursiveAzureResult()

    async def delete_container(self, container):
        self.deleted.append(container)
        return RecursiveAzureResult()

    def get_container_client(self, container):
        return FakeAzureContainerAdmin(self, container)


class FakeAzureContainerAdmin:
    def __init__(self, service, container):
        self.service = service
        self.container = container

    async def set_container_access_policy(self, signed_identifiers, public_access=None):
        self.service.public.append((self.container, signed_identifiers, public_access))
        return RecursiveAzureResult()

    async def list_blobs(self):
        for blob in self.service.blobs:
            yield SimpleNamespace(name=blob)

    async def delete_blobs(self, *blobs, **kwargs):
        self.service.empty_deleted.extend(blobs)
        self.service.empty_delete_kwargs = kwargs
        return [RecursiveAzureResult() for _ in blobs]


def bearer_token(app_state):
    payload = orjson.dumps({"id": 10, "type": 1, "role": 1, "deactivated_at": None}, default=str).decode("utf-8")
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
        "cache_postgres_schema": test_client.app.state.cache_postgres_schema,
        "cache_postgres_table_list": test_client.app.state.cache_postgres_table_list,
        "cache_users_role": test_client.app.state.cache_users_role,
        "client_postgres_pool": test_client.app.state.client_postgres_pool,
        "client_postgres_pool_read": test_client.app.state.client_postgres_pool_read,
        "client_redis": test_client.app.state.client_redis,
        "client_s3": test_client.app.state.client_s3,
        "client_azure_blob": test_client.app.state.client_azure_blob,
        "client_mongodb": test_client.app.state.client_mongodb,
        "config_is_enable_log_api": test_client.app.state.config_is_enable_log_api,
        "config_is_enable_traceback": test_client.app.state.config_is_enable_traceback,
        "config_redis_cache_ttl_sec": test_client.app.state.config_redis_cache_ttl_sec,
        "config_obj_list_limit": test_client.app.state.config_obj_list_limit,
        "config_is_enable_otp_users_update_admin": test_client.app.state.config_is_enable_otp_users_update_admin,
        "config_is_enable_postgres_sql_runner_write": test_client.app.state.config_is_enable_postgres_sql_runner_write,
        "config_is_enable_user_delete": test_client.app.state.config_is_enable_user_delete,
        "func_postgres_create": test_client.app.state.func_postgres_create,
        "func_postgres_update": test_client.app.state.func_postgres_update,
        "func_postgres_delete": test_client.app.state.func_postgres_delete,
        "func_otp_verify": test_client.app.state.func_otp_verify,
    }


    test_client.app.state.cache_postgres_table_list = ["test", "users"]
    test_client.app.state.cache_users_role = {10: 1}
    test_client.app.state.client_postgres_pool = FakePostgresPool()
    test_client.app.state.client_postgres_pool_read = FakePostgresPool()
    test_client.app.state.client_redis = FakeRedis()
    test_client.app.state.client_s3 = FakeS3Admin()
    test_client.app.state.client_azure_blob = FakeAzureAdmin()
    test_client.app.state.client_mongodb = FakeMongo()
    test_client.app.state.config_is_enable_log_api = 0
    test_client.app.state.config_is_enable_traceback = 0
    test_client.app.state.config_redis_cache_ttl_sec = 60
    test_client.app.state.config_is_enable_user_delete = 1
    test_client.app.state.cache_postgres_schema = {
        "test": {"id": {"datatype": "bigint"}, "created_by_id": {"datatype": "bigint"}, "updated_by_id": {"datatype": "bigint"}},
        "users": {"id": {"datatype": "bigint"}, "updated_by_id": {"datatype": "bigint"}},
    }
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
        "/admin/object-create?table=test&mode=buffer",
        headers=bearer_token(admin_client.app.state),
        json={"obj_list": [{"title": "one"}, {"title": "two"}]},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": [101, 102]}
    assert calls["table"] == "test"
    assert calls["mode"] == "buffer"
    assert calls["obj_list"] == [{"title": "one", "created_by_id": 10}, {"title": "two", "created_by_id": 10}]


@pytest.mark.parametrize("mode, attr", [("create", "created"), ("delete", "deleted")])
def test_admin_blob_container_ops_azure_returns_json_safe_result(admin_client, mode, attr):
    response = admin_client.post(
        f"/admin/blob-container-ops?service=azure&mode={mode}&container=images",
        headers=bearer_token(admin_client.app.state),
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": {"service": "azure", "mode": mode, "container": "images"}}
    assert getattr(admin_client.app.state.client_azure_blob, attr) == ["images"]


def test_admin_blob_container_ops_azure_public_sets_blob_access(admin_client):
    response = admin_client.post(
        "/admin/blob-container-ops?service=azure&mode=public&container=images",
        headers=bearer_token(admin_client.app.state),
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": {"service": "azure", "mode": "public", "container": "images"}}
    assert admin_client.app.state.client_azure_blob.public[0][0] == "images"
    assert admin_client.app.state.client_azure_blob.public[0][1] == {}
    assert str(admin_client.app.state.client_azure_blob.public[0][2]) == "PublicAccess.BLOB"


def test_admin_blob_container_ops_azure_empty_deletes_all_blobs(admin_client):
    response = admin_client.post(
        "/admin/blob-container-ops?service=azure&mode=empty&container=images",
        headers=bearer_token(admin_client.app.state),
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": {"service": "azure", "mode": "empty", "container": "images", "deleted": 2}}
    assert admin_client.app.state.client_azure_blob.empty_deleted == ["one.png", "nested/two.png"]
    assert admin_client.app.state.client_azure_blob.empty_delete_kwargs == {"delete_snapshots": "include"}


def test_admin_object_create_allows_restricted_field(admin_client):
    calls = {}

    async def fake_create(**kwargs):
        calls.update(kwargs)
        return [1]

    admin_client.app.state.func_postgres_create = fake_create

    response = admin_client.post(
        "/admin/object-create?table=test",
        headers=bearer_token(admin_client.app.state),
        json={"deactivated_at": None},
    )

    assert response.status_code == 200
    assert calls["obj_list"] == [{"deactivated_at": None, "created_by_id": 10}]


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
    assert "mode" not in update_calls
    assert "config_buffer_limit" not in update_calls


def test_admin_object_delete_passes_schema_without_user_scope(admin_client):
    calls = {}

    async def fake_delete(**kwargs):
        calls.update(kwargs)
        return 2

    admin_client.app.state.func_postgres_delete = fake_delete

    response = admin_client.post(
        "/admin/object-delete",
        headers=bearer_token(admin_client.app.state),
        json={"table": "test", "ids": [1, 2]},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "2 ids deleted"}
    assert calls["cache_postgres_schema"] == admin_client.app.state.cache_postgres_schema
    assert calls["table"] == "test"
    assert calls["ids"] == [1, 2]
    assert calls["created_by_id"] is None
    assert calls["config_is_enable_user_delete"] == 1


def test_admin_postgres_runner_rejects_forbidden_keywords(admin_client):
    response = admin_client.post(
        "/admin/postgres-sql-runner",
        headers=bearer_token(admin_client.app.state),
        json={"mode": "read", "sql": "DELETE FROM test"},
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "read mode restricted"}


def test_admin_postgres_runner_read_returns_rows(admin_client):
    admin_client.app.state.client_postgres_pool_read.conn.fetch_rows = [{"id": 1, "title": "one"}]

    response = admin_client.post(
        "/admin/postgres-sql-runner",
        headers=bearer_token(admin_client.app.state),
        json={"mode": "read", "sql": "select id, title from test"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": [{"id": 1, "title": "one"}]}
    write_pool_sql = [sql for sql, _, _ in admin_client.app.state.client_postgres_pool.conn.fetched_sql]
    assert "select id, title from test" not in write_pool_sql
    assert admin_client.app.state.client_postgres_pool_read.conn.fetched_sql[0][0] == "select id, title from test"


def test_admin_postgres_runner_read_requires_read_pool(admin_client):
    admin_client.app.state.client_postgres_pool_read = None

    response = admin_client.post(
        "/admin/postgres-sql-runner",
        headers=bearer_token(admin_client.app.state),
        json={"mode": "read", "sql": "select id from test"},
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "postgres read client not initialized"}


def test_admin_postgres_runner_write_requires_config(admin_client):
    admin_client.app.state.config_is_enable_postgres_sql_runner_write = 0

    response = admin_client.post(
        "/admin/postgres-sql-runner",
        headers=bearer_token(admin_client.app.state),
        json={"mode": "write", "sql": "update test set title='one' where id=1"},
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "postgres sql runner write mode disabled"}
    assert admin_client.app.state.client_postgres_pool.conn.executed == []


def test_admin_postgres_runner_write_runs_when_enabled(admin_client):
    admin_client.app.state.config_is_enable_postgres_sql_runner_write = 1

    response = admin_client.post(
        "/admin/postgres-sql-runner",
        headers=bearer_token(admin_client.app.state),
        json={"mode": "write", "sql": "update test set title='one' where id=1"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "UPDATE 1"}
    assert admin_client.app.state.client_postgres_pool.conn.executed[0][0] == "update test set title='one' where id=1"


def test_admin_postgres_export_rejects_mutating_sql(admin_client):
    response = admin_client.post(
        "/admin/postgres-export",
        headers=bearer_token(admin_client.app.state),
        json={"sql": "update test set title='x'"},
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "export restricted to select/with/explain/show/describe"}


def test_admin_postgres_export_streams_csv(admin_client):
    admin_client.app.state.client_postgres_pool_read.conn.cursor_rows = [
        {"id": 1, "title": 'one "quoted"'},
        {"id": 2, "title": None},
    ]

    response = admin_client.post(
        "/admin/postgres-export",
        headers=bearer_token(admin_client.app.state),
        json={"sql": "select id,title from test"},
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == "attachment; filename=postgres_export.csv"
    assert response.text == 'id,title\n"1","one ""quoted"""\n"2",\n'


def test_admin_postgres_export_rejects_missing_sql(admin_client):
    response = admin_client.post(
        "/admin/postgres-export",
        headers=bearer_token(admin_client.app.state),
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "parameter 'sql' missing"}


def test_admin_postgres_import_create_processes_csv(admin_client):
    calls = []
    async def fake_create(**kwargs):
        calls.append(kwargs)
        return [1, 2]
    admin_client.app.state.func_postgres_create = fake_create
    
    response = admin_client.post(
        "/admin/postgres-import",
        headers=bearer_token(admin_client.app.state),
        data={"mode": "create", "table": "test"},
        files={"file": ("test.csv", b"title\none\ntwo\n", "text/csv")}
    )
    
    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "2 rows processed"}
    assert len(calls) == 1
    assert calls[0]["obj_list"] == [{"title": "one"}, {"title": "two"}]
    assert calls[0]["table"] == "test"

def test_admin_postgres_import_update_requires_id_column(admin_client):
    response = admin_client.post(
        "/admin/postgres-import",
        headers=bearer_token(admin_client.app.state),
        data={"mode": "update", "table": "test"},
        files={"file": ("test.csv", b"title\nnew\n", "text/csv")}
    )
    assert response.status_code == 400
    assert "requires 'id' column" in response.json()["message"]


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
        [("delete", "cache:1", "cache:2")]
    ]
    assert admin_client.app.state.client_redis.transaction is False


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
