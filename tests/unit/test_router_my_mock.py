import sys
import time
from pathlib import Path

import jwt
import orjson
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.app import app


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class InMemoryMyPool:
    def __init__(self):
        self.conn = InMemoryMyConn()

    def acquire(self):
        return FakeAcquire(self.conn)


class InMemoryMyConn:
    def __init__(self):
        self.users = []
        self.messages = []
        self.log_api = []
        self.parent_rows = []
        self.child_rows = []
        self.executed = []

    async def fetchrow(self, sql, *args):
        normalized = " ".join(sql.lower().split())
        if normalized.startswith("select * from users where id=$1"):
            user_id = args[0]
            rows = [row for row in self.users if row["id"] == user_id]
            return rows[0] if rows else None
        return None

    async def fetch(self, sql, *args):
        normalized = " ".join(sql.lower().split())
        if sql == "profile-test-count":
            user_id = args[0]
            return [{"count": len([row for row in self.child_rows if row.get("created_by_id") == user_id])}]
        if "from log_api" in normalized:
            _days, user_id = args
            usage = {}
            for row in self.log_api:
                if row.get("created_by_id") == user_id:
                    usage[row["path"]] = usage.get(row["path"], 0) + 1
            return [{"api": api, "count": count} for api, count in sorted(usage.items())]
        if "with chat_summary" in normalized:
            return self._message_inbox(user_id=args[0], normalized=normalized)
        if normalized.startswith("select * from message where user_id=$1"):
            return self._message_received(user_id=args[0], normalized=normalized)
        if "select * from message where ((created_by_id=$1 and user_id=$2)" in normalized:
            return self._message_thread(user_one_id=args[0], user_two_id=args[1])
        if "join parent" in normalized:
            user_id = args[0]
            parent_ids = {row["id"] for row in self.parent_rows if row.get("created_by_id") == user_id}
            return [row for row in self.child_rows if row.get("parent_id") in parent_ids]
        return []

    async def execute(self, sql, *args):
        normalized = " ".join(sql.lower().split())
        self.executed.append((sql, args))
        if normalized.startswith("update users set last_active_at=now() where id=$1"):
            user = self._user(args[0])
            if user:
                user["last_active_at"] = "updated"
        elif normalized.startswith("update users set is_deleted=1 where id=$1"):
            user = self._user(args[0])
            if user:
                user["is_deleted"] = 1
        elif normalized.startswith("delete from users where id=$1"):
            self.users = [row for row in self.users if row["id"] != args[0]]
        elif normalized.startswith("update message set is_read=1 where id in"):
            ids = {int(x) for x in sql.split("(", 1)[1].split(")", 1)[0].split(",") if x.strip()}
            for row in self.messages:
                if row["id"] in ids:
                    row["is_read"] = 1
        elif normalized.startswith("update message set is_read=1 where created_by_id=$1 and user_id=$2"):
            sender_id, user_id = args
            for row in self.messages:
                if row.get("created_by_id") == sender_id and row.get("user_id") == user_id:
                    row["is_read"] = 1
        elif normalized.startswith("delete from message where id=$1"):
            message_id, user_id = args
            self.messages = [
                row
                for row in self.messages
                if not (row["id"] == message_id and user_id in (row.get("created_by_id"), row.get("user_id")))
            ]
        elif normalized.startswith("delete from message where created_by_id=$1"):
            self.messages = [row for row in self.messages if row.get("created_by_id") != args[0]]
        elif normalized.startswith("delete from message where user_id=$1"):
            self.messages = [row for row in self.messages if row.get("user_id") != args[0]]
        elif normalized.startswith("delete from message where (created_by_id=$1 or user_id=$1)"):
            self.messages = [
                row for row in self.messages if args[0] not in (row.get("created_by_id"), row.get("user_id"))
            ]
        return "OK"

    def seed_user(self, **kwargs):
        row = {
            "id": kwargs.pop("id", len(self.users) + 1),
            "type": kwargs.pop("type", 1),
            "role": kwargs.pop("role", None),
            "is_active": kwargs.pop("is_active", 1),
            "is_deleted": kwargs.pop("is_deleted", 0),
            "email": kwargs.pop("email", None),
            "username": kwargs.pop("username", None),
            "last_active_at": kwargs.pop("last_active_at", None),
        }
        row.update(kwargs)
        self.users.append(row)
        return row

    def seed_message(self, **kwargs):
        row = {
            "id": kwargs.pop("id", len(self.messages) + 1),
            "created_by_id": kwargs.pop("created_by_id"),
            "user_id": kwargs.pop("user_id"),
            "description": kwargs.pop("description", "hello"),
            "is_read": kwargs.pop("is_read", 0),
        }
        row.update(kwargs)
        self.messages.append(row)
        return row

    def _user(self, user_id):
        rows = [row for row in self.users if row["id"] == user_id]
        return rows[0] if rows else None

    def _message_received(self, *, user_id, normalized):
        rows = [row for row in self.messages if row.get("user_id") == user_id]
        if "is_read=1" in normalized:
            rows = [row for row in rows if row.get("is_read") == 1]
        elif "is_read is distinct from 1" in normalized:
            rows = [row for row in rows if row.get("is_read") != 1]
        return sorted(rows, key=lambda row: row["id"], reverse=True)

    def _message_thread(self, *, user_one_id, user_two_id):
        rows = [
            row
            for row in self.messages
            if (row.get("created_by_id"), row.get("user_id")) in ((user_one_id, user_two_id), (user_two_id, user_one_id))
        ]
        return sorted(rows, key=lambda row: row["id"], reverse=True)

    def _message_inbox(self, *, user_id, normalized):
        latest_by_conversation = {}
        for row in self.messages:
            if user_id not in (row.get("created_by_id"), row.get("user_id")):
                continue
            conversation_id = abs(row["created_by_id"] - row["user_id"])
            if conversation_id not in latest_by_conversation or row["id"] > latest_by_conversation[conversation_id]["id"]:
                latest_by_conversation[conversation_id] = row
        rows = list(latest_by_conversation.values())
        if "user_id=$1 and is_read=1" in normalized:
            rows = [row for row in rows if row.get("user_id") == user_id and row.get("is_read") == 1]
        elif "user_id=$1 and is_read is distinct from 1" in normalized:
            rows = [row for row in rows if row.get("user_id") == user_id and row.get("is_read") != 1]
        return sorted(rows, key=lambda row: row["id"], reverse=True)


class FakeMongoCollection:
    async def insert_many(self, obj_list):
        self.obj_list = obj_list
        return type("InsertManyResult", (), {"inserted_ids": ["id-one", "id-two"]})()


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


def bearer_token(app_state, user):
    payload = orjson.dumps(user, default=str).decode("utf-8")
    token = jwt.encode({"exp": int(time.time()) + 3600, "data": payload, "type": "access"}, app_state.config_token_secret_key)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def my_test_client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def my_client(my_test_client):
    test_client = my_test_client
    originals = {
        "client_postgres_pool": test_client.app.state.client_postgres_pool,
        "client_mongodb": test_client.app.state.client_mongodb,
        "config_is_enable_log_api": test_client.app.state.config_is_enable_log_api,
        "config_sql": test_client.app.state.config_sql,
        "cache_postgres_table_list": test_client.app.state.cache_postgres_table_list,
        "cache_postgres_column_list": test_client.app.state.cache_postgres_column_list,
        "config_obj_list_limit": test_client.app.state.config_obj_list_limit,
        "func_postgres_delete": test_client.app.state.func_postgres_delete,
        "func_postgres_read": test_client.app.state.func_postgres_read,
        "func_postgres_create": test_client.app.state.func_postgres_create,
        "func_postgres_update": test_client.app.state.func_postgres_update,
        "func_otp_verify": test_client.app.state.func_otp_verify,
    }


    test_client.app.state.client_postgres_pool = InMemoryMyPool()
    test_client.app.state.client_mongodb = FakeMongo()
    test_client.app.state.config_is_enable_log_api = 0
    test_client.app.state.config_sql = {"profile_metadata": {"test_count": "profile-test-count"}}
    test_client.app.state.cache_postgres_table_list = ["test", "users", "message", "parent", "child"]
    test_client.app.state.cache_postgres_column_list = ["id", "created_by_id", "parent_id"]
    try:
        yield test_client
    finally:
        for key, value in originals.items():
            setattr(test_client.app.state, key, value)


@pytest.fixture()
def auth_headers(my_client):
    user = my_client.app.state.client_postgres_pool.conn.seed_user(
        id=10, email="my-user@example.com", username="myuser"
    )
    return bearer_token(my_client.app.state, {"id": user["id"], "type": user["type"], "role": user["role"], "is_active": 1})


def test_my_profile_returns_user_metadata_token_and_updates_last_active(my_client, auth_headers):
    conn = my_client.app.state.client_postgres_pool.conn
    conn.child_rows.append({"id": 1, "created_by_id": 10, "title": "owned"})

    response = my_client.get("/my/profile", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == 1
    assert body["message"]["id"] == 10
    assert body["message"]["test_count"] == [{"count": 1}]
    assert body["message"]["token"]["token"]
    assert conn._user(10)["last_active_at"] == "updated"


def test_my_token_refresh_returns_new_token(my_client, auth_headers):
    response = my_client.post("/my/token-refresh", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == 1
    assert body["message"]["token"]
    assert body["message"]["token_refresh"]


def test_my_api_usage_groups_logs_for_authenticated_user(my_client, auth_headers):
    conn = my_client.app.state.client_postgres_pool.conn
    conn.log_api.extend(
        [
            {"created_by_id": 10, "path": "/my/profile"},
            {"created_by_id": 10, "path": "/my/profile"},
            {"created_by_id": 11, "path": "/my/profile"},
            {"created_by_id": 10, "path": "/my/object-read"},
        ]
    )

    response = my_client.get("/my/api-usage?days=7", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["message"] == [
        {"api": "/my/object-read", "count": 1},
        {"api": "/my/profile", "count": 2},
    ]


def test_my_account_delete_soft_marks_user_deleted(my_client, auth_headers):
    response = my_client.delete("/my/account-delete?mode=soft", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "account deleted"}
    assert my_client.app.state.client_postgres_pool.conn._user(10)["is_deleted"] == 1


def test_my_account_delete_rejects_role_user(my_client):
    my_client.app.state.client_postgres_pool.conn.seed_user(id=20, role=1)
    headers = bearer_token(my_client.app.state, {"id": 20, "type": 1, "role": 1, "is_active": 1})

    response = my_client.delete("/my/account-delete?mode=hard", headers=headers)

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "account with role cannot be deleted"}


def test_my_message_received_returns_unread_and_marks_them_read(my_client, auth_headers):
    conn = my_client.app.state.client_postgres_pool.conn
    conn.seed_message(id=1, created_by_id=20, user_id=10, is_read=0)
    conn.seed_message(id=2, created_by_id=21, user_id=10, is_read=1)

    response = my_client.get("/my/message-received?mode=unread", headers=auth_headers)

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["message"]] == [1]
    assert conn.messages[0]["is_read"] == 1


def test_my_message_inbox_returns_latest_unread_conversations(my_client, auth_headers):
    conn = my_client.app.state.client_postgres_pool.conn
    conn.seed_message(id=1, created_by_id=20, user_id=10, is_read=0)
    conn.seed_message(id=2, created_by_id=10, user_id=20, is_read=0)
    conn.seed_message(id=3, created_by_id=30, user_id=10, is_read=0)

    response = my_client.get("/my/message-inbox?mode=unread", headers=auth_headers)

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["message"]] == [3]


def test_my_message_thread_returns_conversation_and_marks_received_read(my_client, auth_headers):
    conn = my_client.app.state.client_postgres_pool.conn
    conn.seed_message(id=1, created_by_id=20, user_id=10, is_read=0)
    conn.seed_message(id=2, created_by_id=10, user_id=20, is_read=1)
    conn.seed_message(id=3, created_by_id=30, user_id=10, is_read=0)

    response = my_client.get("/my/message-thread?user_id=20", headers=auth_headers)

    assert response.status_code == 200
    assert [row["id"] for row in response.json()["message"]] == [2, 1]
    assert conn.messages[0]["is_read"] == 1
    assert conn.messages[2]["is_read"] == 0


def test_my_message_delete_single_deletes_only_owned_message(my_client, auth_headers):
    conn = my_client.app.state.client_postgres_pool.conn
    conn.seed_message(id=1, created_by_id=10, user_id=20)
    conn.seed_message(id=2, created_by_id=30, user_id=40)

    response = my_client.delete("/my/message-delete-single?id=1", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "message deleted"}
    assert [row["id"] for row in conn.messages] == [2]


def test_my_message_delete_bulk_deletes_received_messages(my_client, auth_headers):
    conn = my_client.app.state.client_postgres_pool.conn
    conn.seed_message(id=1, created_by_id=20, user_id=10)
    conn.seed_message(id=2, created_by_id=10, user_id=20)

    response = my_client.delete("/my/message-delete-bulk?mode=received", headers=auth_headers)

    assert response.status_code == 200
    assert [row["id"] for row in conn.messages] == [2]




def test_my_ids_delete_passes_user_scope_to_delete_helper(my_client, auth_headers):
    calls = {}

    async def fake_delete(**kwargs):
        calls.update(kwargs)
        return "deleted"

    my_client.app.state.func_postgres_delete = fake_delete

    response = my_client.post("/my/ids-delete", headers=auth_headers, json={"table": "test", "ids": [1, 2]})

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "deleted"}
    assert calls["table"] == "test"
    assert calls["ids"] == [1, 2]
    assert calls["created_by_id"] == 10


def test_my_object_create_passes_authenticated_user_to_postgres_create(my_client, auth_headers):
    calls = {}

    async def fake_create(**kwargs):
        calls.update(kwargs)
        return [101]

    my_client.app.state.func_postgres_create = fake_create

    response = my_client.post(
        "/my/object-create?table=test&mode=now",
        headers=auth_headers,
        json={"obj_list": [{"title": "one"}]},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": [101]}
    assert calls["table"] == "test"
    assert calls["obj_list"] == [{"title": "one", "created_by_id": 10}]


def test_my_object_create_rejects_disabled_table_at_api(my_client, auth_headers):
    response = my_client.post(
        "/my/object-create?table=users",
        headers=auth_headers,
        json={"email": "a@example.com"},
    )

    assert response.status_code == 400
    assert "creation disabled for table: users" in response.json()["message"]


def test_my_object_create_rejects_restricted_field_at_api(my_client, auth_headers):
    response = my_client.post(
        "/my/object-create?table=test",
        headers=auth_headers,
        json={"is_active": 1},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "unauthorized creation of restricted field: is_active"


def test_my_object_update_passes_otp_and_payload_to_postgres_update(my_client, auth_headers):
    calls = {}

    async def fake_update(**kwargs):
        calls.update(kwargs)
        return "updated"

    my_client.app.state.func_postgres_update = fake_update

    response = my_client.put(
        "/my/object-update?table=test&otp=123456",
        headers=auth_headers,
        json={"id": 1, "title": "changed"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "updated"}
    assert calls["created_by_id"] == 10
    assert calls["obj_list"] == [{"id": 1, "title": "changed", "updated_by_id": 10}]
    assert "mode" not in calls
    assert "config_buffer_limit" not in calls


def test_my_object_update_rejects_restricted_field_at_api(my_client, auth_headers):
    response = my_client.put(
        "/my/object-update?table=test",
        headers=auth_headers,
        json={"id": 1, "is_active": 1},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "unauthorized update to restricted field: is_active"


def test_my_object_update_rejects_multi_user_update_at_api(my_client, auth_headers):
    response = my_client.put(
        "/my/object-update?table=users",
        headers=auth_headers,
        json={"obj_list": [{"id": 10, "username": "user_1"}, {"id": 10, "username": "user_2"}]},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "multi-object user update restricted"


def test_my_object_update_rejects_other_user_at_api(my_client, auth_headers):
    response = my_client.put(
        "/my/object-update?table=users",
        headers=auth_headers,
        json={"id": 11, "username": "user_1"},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "ownership issue: cannot update other users"


def test_my_object_update_rejects_combined_sensitive_user_field_at_api(my_client, auth_headers):
    response = my_client.put(
        "/my/object-update?table=users",
        headers=auth_headers,
        json={"id": 10, "username": "user_1", "title": "extra"},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "sensitive fields must be updated individually (item length 2 required)"


def test_my_object_update_verifies_otp_for_user_email_at_api(my_client, auth_headers):
    otp_calls = {}

    async def fake_otp(**kwargs):
        otp_calls.update(kwargs)
        return None

    async def fake_update(**_kwargs):
        return "updated"

    my_client.app.state.func_otp_verify = fake_otp
    my_client.app.state.func_postgres_update = fake_update

    response = my_client.put(
        "/my/object-update?table=users&otp=123456",
        headers=auth_headers,
        json={"id": 10, "email": "new@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "updated"}
    assert otp_calls["otp"] == 123456
    assert otp_calls["email"] == "new@example.com"


def test_my_object_read_filters_by_authenticated_user(my_client, auth_headers):
    calls = {}

    async def fake_read(**kwargs):
        calls.update(kwargs)
        return [{"id": 1, "created_by_id": 10}]

    my_client.app.state.func_postgres_read = fake_read

    response = my_client.get("/my/object-read?table=test", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["message"] == [{"id": 1, "created_by_id": 10}]
    assert "created_by_id = 10" in str(calls["filter"])


def test_my_object_create_mongodb_uses_mocked_client(my_client, auth_headers):
    response = my_client.post(
        "/my/object-create-mongodb?database=atom&table=items",
        headers=auth_headers,
        json={"obj_list": [{"title": "one"}, {"title": "two"}]},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": ["id-one", "id-two"]}
    assert my_client.app.state.client_mongodb.collection.obj_list == [{"title": "one"}, {"title": "two"}]
