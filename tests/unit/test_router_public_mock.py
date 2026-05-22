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
from core.router import public as public_router


def bearer_token(app_state, user):
    payload = orjson.dumps(user, default=str).decode("utf-8")
    token = jwt.encode({"exp": int(time.time()) + 3600, "data": payload, "type": "access"}, app_state.config_token_secret_key)
    return {"Authorization": f"Bearer {token}"}


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class InMemoryPublicPool:
    def __init__(self):
        self.conn = InMemoryPublicConn()

    def acquire(self):
        return FakeAcquire(self.conn)


class InMemoryPublicConn:
    def __init__(self):
        self.otp = []
        self.tag_rows = []
        self.next_otp_id = 1
        self.executed = []

    async def fetch(self, sql, *args):
        normalized = " ".join(sql.lower().split())
        if "from otp where email=$1" in normalized:
            return self._latest_otp(lambda row: row.get("email") == args[0])
        if "from otp where mobile=$1" in normalized:
            return self._latest_otp(lambda row: row.get("mobile") == args[0])
        if "cross join lateral unnest" in normalized:
            filter_value = args[0] if args else None
            counts = {}
            for row in self.tag_rows:
                if filter_value is not None and row.get("type") != filter_value:
                    continue
                for tag in row.get("tag", []):
                    counts[tag] = counts.get(tag, 0) + 1
            return [
                {"item_col": tag, "agg_val": count}
                for tag, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
            ]
        return []

    async def execute(self, sql, *args):
        self.executed.append((sql, args))
        if sql.lower().startswith("insert into otp"):
            otp, email, mobile = args
            self.seed_otp(otp=otp, email=email, mobile=mobile)
        return "OK"

    def seed_otp(self, *, otp, email=None, mobile=None, is_valid=True):
        row = {"id": self.next_otp_id, "otp": otp, "email": email, "mobile": mobile, "is_valid": is_valid}
        self.next_otp_id += 1
        self.otp.append(row)
        return row

    def _latest_otp(self, predicate):
        rows = [row for row in self.otp if predicate(row)]
        return sorted(rows, key=lambda row: row["id"], reverse=True)[:1]


class FakeSes:
    def __init__(self):
        self.calls = []

    def send_email(self, **kwargs):
        self.calls.append(kwargs)
        return {"MessageId": "ses-message"}


class FakeSns:
    def __init__(self):
        self.calls = []

    def publish(self, **kwargs):
        self.calls.append(kwargs)
        return {"MessageId": "sns-message"}


class FakeHttpResponse:
    def __init__(self, *, status_code=200, payload=None, text="ok"):
        self.status_code = status_code
        self._payload = payload or {"ok": True}
        self.text = text

    def json(self):
        return self._payload


class FakeAsyncClient:
    response = FakeHttpResponse()
    post_calls = []
    get_calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        self.__class__.post_calls.append((args, kwargs))
        return self.__class__.response

    async def get(self, *args, **kwargs):
        self.__class__.get_calls.append((args, kwargs))
        return self.__class__.response


@pytest.fixture(scope="module")
def public_test_client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def public_client(public_test_client, monkeypatch):
    test_client = public_test_client
    originals = {
        "client_postgres_pool": test_client.app.state.client_postgres_pool,
        "client_ses": test_client.app.state.client_ses,
        "client_sns": test_client.app.state.client_sns,
        "config_is_enable_log_api": test_client.app.state.config_is_enable_log_api,
        "config_resend_url": test_client.app.state.config_resend_url,
        "config_resend_key": test_client.app.state.config_resend_key,
        "config_fast2sms_url": test_client.app.state.config_fast2sms_url,
        "config_fast2sms_key": test_client.app.state.config_fast2sms_key,
        "config_email_sender_default": test_client.app.state.config_email_sender_default,
        "cache_postgres_table_list": test_client.app.state.cache_postgres_table_list,
        "cache_postgres_column_list": test_client.app.state.cache_postgres_column_list,
        "cache_api_response": test_client.app.state.cache_api_response,
        "cache_postgres_schema": test_client.app.state.cache_postgres_schema,
        "config_table_read_enable_public": test_client.app.state.config_table_read_enable_public,
        "config_obj_list_limit": test_client.app.state.config_obj_list_limit,
        "func_postgres_create": test_client.app.state.func_postgres_create,
        "func_postgres_read": test_client.app.state.func_postgres_read,
        "func_postgres_serialize": test_client.app.state.func_postgres_serialize,
        "func_otp_generate": test_client.app.state.func_otp_generate,
        "func_otp_verify": test_client.app.state.func_otp_verify,
        "config_query_limit_default": getattr(test_client.app.state, "config_query_limit_default", 100),
    }


    async def passthrough_serialize(**kwargs):
        return kwargs["obj_list"]

    test_client.app.state.client_postgres_pool = InMemoryPublicPool()
    test_client.app.state.client_ses = FakeSes()
    test_client.app.state.client_sns = FakeSns()
    test_client.app.state.config_is_enable_log_api = 0
    test_client.app.state.config_resend_url = "https://resend.test/emails"
    test_client.app.state.config_resend_key = "resend-key"
    test_client.app.state.config_fast2sms_url = "https://fast2sms.test/send"
    test_client.app.state.config_fast2sms_key = "fast2sms-key"
    test_client.app.state.config_email_sender_default = "sender@example.com"
    test_client.app.state.cache_postgres_table_list = ["test", "post", "users"]
    test_client.app.state.cache_postgres_column_list = ["id", "type", "tag", "category", "created_by_id"]
    test_client.app.state.cache_api_response = {}
    test_client.app.state.cache_postgres_schema = {"test": {"id": {"datatype": "int"}, "type": {"datatype": "text"}, "tag": {"datatype": "text[]"}, "category": {"datatype": "text"}, "created_by_id": {"datatype": "bigint"}}}
    test_client.app.state.config_table_read_enable_public = ["*"]
    test_client.app.state.config_query_limit_default = 100
    test_client.app.state.func_postgres_serialize = passthrough_serialize
    FakeAsyncClient.response = FakeHttpResponse()
    FakeAsyncClient.post_calls = []
    FakeAsyncClient.get_calls = []
    monkeypatch.setattr(public_router.httpx, "AsyncClient", FakeAsyncClient)
    try:
        yield test_client
    finally:
        for key, value in originals.items():
            setattr(test_client.app.state, key, value)


def test_public_converter_number_encodes_and_decodes(public_client):
    encoded = public_client.get("/public/converter-number?datatype=int&mode=encode&x=abc")

    assert encoded.status_code == 200
    assert encoded.json()["status"] == 1

    decoded = public_client.get(
        f"/public/converter-number?datatype=int&mode=decode&x={encoded.json()['message']}"
    )

    assert decoded.status_code == 200
    assert decoded.json() == {"status": 1, "message": "abc"}


def test_public_converter_number_rejects_invalid_character(public_client):
    response = public_client.get("/public/converter-number?datatype=int&mode=encode&x=bad!")

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "invalid character in input"}


def test_public_object_create_passes_public_scope_to_postgres_create(public_client):
    calls = {}

    async def fake_create(**kwargs):
        calls.update(kwargs)
        return [1]

    public_client.app.state.func_postgres_create = fake_create

    response = public_client.post(
        "/public/object-create?table=test&mode=now",
        json={"obj_list": [{"title": "public item"}]},
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": [1]}
    assert calls["table"] == "test"
    assert calls["obj_list"] == [{"title": "public item"}]


def test_public_object_create_sets_owner_when_token_present(public_client):
    calls = {}

    async def fake_create(**kwargs):
        calls.update(kwargs)
        return [1]

    public_client.app.state.func_postgres_create = fake_create

    response = public_client.post(
        "/public/object-create?table=test",
        headers=bearer_token(public_client.app.state, {"id": 99, "type": 1, "role": 1, "deactivated_at": None}),
        json={"title": "public item"},
    )

    assert response.status_code == 200
    assert calls["obj_list"] == [{"title": "public item", "created_by_id": 99}]


def test_public_object_create_rejects_disallowed_table_at_api(public_client):
    response = public_client.post("/public/object-create?table=users", json={"email": "a@example.com"})

    assert response.status_code == 400
    assert "creation disabled for table: users" in response.json()["message"]


def test_public_object_create_rejects_restricted_field_at_api(public_client):
    response = public_client.post("/public/object-create?table=test", json={"deactivated_at": None})

    assert response.status_code == 400
    assert response.json()["message"] == "unauthorized creation of restricted field: deactivated_at"


def test_public_object_create_rejects_deleted_at_at_api(public_client):
    response = public_client.post(
        "/public/object-create?table=test",
        json={"deleted_at": "2026-05-21T12:00:00Z"},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "deleted_at cannot be set on create; use deactivated_at for reversible inactive state"


def test_public_object_read_allows_configured_table(public_client):
    calls = {}

    async def fake_read(**kwargs):
        calls.update(kwargs)
        return [{"id": 1, "title": "public"}]

    public_client.app.state.func_postgres_read = fake_read

    response = public_client.get("/public/object-read?table=test&filter=" + orjson.dumps(["type = 1"]).decode())

    assert response.status_code == 200
    assert response.json()["message"] == [{"id": 1, "title": "public"}]
    assert calls["table"] == "test"
    assert "type =" in str(calls["filter"])


def test_public_object_read_rejects_disallowed_table_when_wildcard_not_set(public_client):
    public_client.app.state.config_table_read_enable_public = ["test", "post"]
    response = public_client.get("/public/object-read?table=users")
    assert response.status_code == 400
    assert "read disabled for table: users" in response.json()["message"]


def test_public_object_read_allows_all_tables_when_wildcard_set(public_client):
    public_client.app.state.config_table_read_enable_public = ["*"]
    calls = {}

    async def fake_read(**kwargs):
        calls.update(kwargs)
        return [{"id": 1}]

    public_client.app.state.func_postgres_read = fake_read
    response = public_client.get("/public/object-read?table=users")
    assert response.status_code == 200
    assert calls["table"] == "users"


def test_public_otp_verify_email_uses_seeded_otp(public_client):
    public_client.app.state.client_postgres_pool.conn.seed_otp(otp=123456, email="otp@example.com")

    response = public_client.get("/public/otp-verify-email?email=otp@example.com&otp=123456")

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "done"}


def test_public_otp_verify_mobile_rejects_invalid_otp(public_client):
    public_client.app.state.client_postgres_pool.conn.seed_otp(otp=123456, mobile="+15550101111")

    response = public_client.get("/public/otp-verify-mobile?mobile=%2B15550101111&otp=999999")

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "invalid otp code"}


def test_public_otp_send_email_ses_generates_otp_and_calls_ses(public_client):
    async def fake_generate(**kwargs):
        assert kwargs["email"] == "to@example.com"
        assert kwargs["mobile"] is None
        assert kwargs["config_otp_length"] == public_client.app.state.config_otp_length
        return 111222

    public_client.app.state.func_otp_generate = fake_generate

    response = public_client.post("/public/otp-send-email-ses?email=to@example.com")

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "done"}
    call = public_client.app.state.client_ses.calls[0]
    assert call["Source"] == "sender@example.com"
    assert call["Destination"] == {"ToAddresses": ["to@example.com"]}
    assert call["Message"]["Body"]["Html"]["Data"] == "111222"


def test_public_otp_send_email_resend_posts_payload(public_client):
    async def fake_generate(**_kwargs):
        return 333444

    public_client.app.state.func_otp_generate = fake_generate

    response = public_client.post(
        "/public/otp-send-email-resend?email=to@example.com&sender=custom@example.com"
    )

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "done"}
    args, kwargs = FakeAsyncClient.post_calls[0]
    assert args == ("https://resend.test/emails",)
    assert kwargs["headers"]["Authorization"] == "Bearer resend-key"
    assert "333444" in kwargs["data"]
    assert "custom@example.com" in kwargs["data"]


def test_public_otp_send_email_resend_reports_provider_error(public_client):
    async def fake_generate(**_kwargs):
        return 333444

    public_client.app.state.func_otp_generate = fake_generate
    FakeAsyncClient.response = FakeHttpResponse(status_code=500, text="provider down")

    response = public_client.post("/public/otp-send-email-resend?email=to@example.com")

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "failed to send email: provider down"}


def test_public_otp_send_mobile_sns_calls_publish(public_client):
    async def fake_generate(**kwargs):
        assert kwargs["email"] is None
        assert kwargs["mobile"] == "+15550101111"
        return 555666

    public_client.app.state.func_otp_generate = fake_generate

    response = public_client.post("/public/otp-send-mobile-sns?mobile=%2B15550101111")

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": "done"}
    assert public_client.app.state.client_sns.calls[0] == {
        "PhoneNumber": "+15550101111",
        "Message": "555666",
    }


def test_public_otp_send_mobile_sns_template_replaces_otp(public_client):
    async def fake_generate(**_kwargs):
        return 777888

    public_client.app.state.func_otp_generate = fake_generate

    response = public_client.post(
        "/public/otp-send-mobile-sns-template",
        json={
            "mobile": "+15550101111",
            "message": "Your code is {otp}",
            "template_id": "template-1",
            "entity_id": "entity-1",
            "sender_id": "ATOM",
        },
    )

    assert response.status_code == 200
    call = public_client.app.state.client_sns.calls[0]
    assert call["Message"] == "Your code is 777888"
    assert call["MessageAttributes"]["AWS.SNS.SMS.SenderID"]["StringValue"] == "ATOM"
    assert call["MessageAttributes"]["AWS.MM.SMS.TemplateId"]["StringValue"] == "template-1"
    assert call["MessageAttributes"]["AWS.MM.SMS.EntityId"]["StringValue"] == "entity-1"


def test_public_otp_send_mobile_fast2sms_returns_provider_json(public_client):
    async def fake_generate(**_kwargs):
        return 999000

    public_client.app.state.func_otp_generate = fake_generate
    FakeAsyncClient.response = FakeHttpResponse(payload={"return": True, "request_id": "fast-id"})

    response = public_client.post("/public/otp-send-mobile-fast2sms?mobile=15550101111")

    assert response.status_code == 200
    assert response.json() == {"status": 1, "message": {"return": True, "request_id": "fast-id"}}
    args, kwargs = FakeAsyncClient.get_calls[0]
    assert args == ("https://fast2sms.test/send",)
    assert kwargs["params"] == {
        "authorization": "fast2sms-key",
        "route": "otp",
        "variables_values": "999000",
        "numbers": "15550101111",
    }


def test_public_jira_worklog_export_streams_csv(public_client, monkeypatch):
    class FakeUser:
        def __init__(self, name):
            self.displayName = name

    class FakeIssue:
        id = "ISSUE-1"
        fields = type("Fields", (), {"assignee": FakeUser("Alice")})()

    class FakeWorklog:
        started = "2026-05-01T12:00:00.000+0000"
        timeSpentSeconds = 7200
        author = FakeUser("Bob")

    class FakeJira:
        def __init__(self, *, server, basic_auth):
            assert server == "https://jira.example.com"
            assert basic_auth == ("jira@example.com", "token")

        def enhanced_search_issues(self, jql, maxResults):
            assert "2026-05-01" in jql
            assert maxResults == 0
            return [FakeIssue()]

        def worklogs(self, issue_id):
            assert issue_id == "ISSUE-1"
            return [FakeWorklog()]

    monkeypatch.setitem(sys.modules, "jira", types.SimpleNamespace(JIRA=FakeJira))

    response = public_client.post(
        "/public/jira-worklog-export",
        json={
            "url": "https://jira.example.com",
            "email": "jira@example.com",
            "api_token": "token",
            "start_date": "2026-05-01",
            "end_date": "2026-05-02",
        },
    )

    assert response.status_code == 200
    assert "attachment;" in response.headers["content-disposition"]
    assert "2026-05-01" in response.text
    assert "Alice" in response.text
    assert "Bob" in response.text


def test_public_table_groupby_counts_with_filter(public_client):
    public_client.app.state.client_postgres_pool.conn.tag_rows.extend(
        [
            {"id": 1, "type": "news", "tag": ["python", "api"]},
            {"id": 2, "type": "news", "tag": ["python"]},
            {"id": 3, "type": "docs", "tag": ["api"]},
        ]
    )

    response = public_client.get(
        "/public/table-groupby?table=test&col=tag&filter=" + orjson.dumps(["type = 'news'"]).decode()
    )

    assert response.status_code == 200
    assert response.json()["message"] == [{"item": "python", "value": 2}, {"item": "api", "value": 1}]


def test_public_table_groupby_rejects_invalid_identifier(public_client):
    original_tables = public_client.app.state.cache_postgres_table_list
    public_client.app.state.cache_postgres_table_list = ["bad-table"]
    try:
        response = public_client.get("/public/table-groupby?table=bad-table&col=tag")
    finally:
        public_client.app.state.cache_postgres_table_list = original_tables

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "invalid identifier"}
