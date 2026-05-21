import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.app import app
from core.router import auth as auth_router


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class InMemoryAuthPool:
    def __init__(self):
        self.conn = InMemoryAuthConn()

    def acquire(self):
        return FakeAcquire(self.conn)


class InMemoryAuthConn:
    def __init__(self):
        self.users = []
        self.otp = []
        self.next_user_id = 1
        self.next_otp_id = 1

    async def fetch(self, sql, *args):
        normalized = " ".join(sql.lower().split())
        if normalized.startswith("insert into users"):
            return [self._insert_user(sql, args)]
        if "from users where type=$1 and username=$2" in normalized:
            type_, username = args
            return self._latest_user(lambda row: row.get("type") == type_ and row.get("username") == username)
        if "from users where type=$1 and email=$2" in normalized:
            type_, email = args
            return self._latest_user(lambda row: row.get("type") == type_ and row.get("email") == email)
        if "from users where type=$1 and mobile=$2" in normalized:
            type_, mobile = args
            return self._latest_user(lambda row: row.get("type") == type_ and row.get("mobile") == mobile)
        if "from users where google_login_id=$1 and type=$2" in normalized:
            google_login_id, type_ = args
            return self._latest_user(lambda row: row.get("google_login_id") == google_login_id and row.get("type") == type_)
        if "from otp where email=$1" in normalized:
            return self._latest_otp(lambda row: row.get("email") == args[0])
        if "from otp where mobile=$1" in normalized:
            return self._latest_otp(lambda row: row.get("mobile") == args[0])
        return []

    def seed_user(self, **kwargs):
        row = self._base_user()
        row.update(kwargs)
        if row["id"] is None:
            row["id"] = self.next_user_id
            self.next_user_id += 1
        else:
            self.next_user_id = max(self.next_user_id, row["id"] + 1)
        self.users.append(row)
        return row

    def seed_otp(self, *, otp, email=None, mobile=None, is_valid=True):
        row = {"id": self.next_otp_id, "otp": otp, "email": email, "mobile": mobile, "is_valid": is_valid}
        self.next_otp_id += 1
        self.otp.append(row)
        return row

    def _insert_user(self, sql, args):
        columns = sql.split("(", 1)[1].split(")", 1)[0].replace(" ", "").split(",")
        return self.seed_user(**dict(zip(columns, args)))

    def _latest_user(self, predicate):
        rows = [row for row in self.users if predicate(row)]
        return sorted(rows, key=lambda row: row["id"], reverse=True)[:1]

    def _latest_otp(self, predicate):
        rows = [row for row in self.otp if predicate(row)]
        return sorted(rows, key=lambda row: row["id"], reverse=True)[:1]

    def _base_user(self):
        return {
            "id": None,
            "type": None,
            "username": None,
            "password": None,
            "google_login_id": None,
            "google_login_metadata": None,
            "email": None,
            "mobile": None,
            "role": None,
            "deactivated_at": None,
            "verified_at": 0,
            "name": None,
        }


@pytest.fixture()
def auth_client():
    with TestClient(app) as test_client:
        original_pool = test_client.app.state.client_postgres_pool
        original_log = test_client.app.state.config_is_enable_log_api
        original_traceback = test_client.app.state.config_is_enable_traceback
        test_client.app.state.client_postgres_pool = InMemoryAuthPool()
        test_client.app.state.config_is_enable_log_api = 0
        test_client.app.state.config_is_enable_traceback = 0
        try:
            yield test_client
        finally:
            test_client.app.state.client_postgres_pool = original_pool
            test_client.app.state.config_is_enable_log_api = original_log
            test_client.app.state.config_is_enable_traceback = original_traceback


def assert_auth_success(response, *, expected_user, app_state):
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == 1
    user = body["message"]["user"]
    token = body["message"]["token"]
    for key, value in expected_user.items():
        assert user[key] == value
    assert token["token"]
    assert token["token_refresh"]
    assert token["token_expiry_sec"] == app_state.config_token_expiry_sec


def test_signup_username_password_creates_user_and_returns_tokens(auth_client):
    response = auth_client.post(
        "/auth/signup-username-password",
        json={"type": 1, "username": "test_user", "password": "secret123"},
    )

    assert_auth_success(
        response,
        expected_user={"type": 1, "username": "test_user", "deactivated_at": None},
        app_state=auth_client.app.state,
    )
    user = auth_client.app.state.client_postgres_pool.conn.users[0]
    assert user["password"] != "secret123"
    auth_client.app.state.client_password_hasher.verify(user["password"], "secret123")


def test_login_username_password_uses_seeded_password_hash(auth_client):
    password_hash = auth_client.app.state.client_password_hasher.hash("secret123")
    auth_client.app.state.client_postgres_pool.conn.seed_user(type=1, username="test_user", password=password_hash)

    response = auth_client.post(
        "/auth/login-username-password",
        json={"type": 1, "username": "test_user", "password": "secret123"},
    )

    assert_auth_success(response, expected_user={"type": 1, "username": "test_user"}, app_state=auth_client.app.state)


def test_login_username_password_rejects_bad_password(auth_client):
    password_hash = auth_client.app.state.client_password_hasher.hash("secret123")
    auth_client.app.state.client_postgres_pool.conn.seed_user(type=1, username="test_user", password=password_hash)

    response = auth_client.post(
        "/auth/login-username-password",
        json={"type": 1, "username": "test_user", "password": "wrong123"},
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "incorrect password"}


def test_login_email_password_uses_seeded_user(auth_client):
    password_hash = auth_client.app.state.client_password_hasher.hash("secret123")
    auth_client.app.state.client_postgres_pool.conn.seed_user(
        type=1, email="auth-email@example.com", password=password_hash
    )

    response = auth_client.post(
        "/auth/login-email-password",
        json={"type": 1, "email": "auth-email@example.com", "password": "secret123"},
    )

    assert_auth_success(
        response,
        expected_user={"type": 1, "email": "auth-email@example.com"},
        app_state=auth_client.app.state,
    )


def test_login_mobile_password_uses_seeded_user(auth_client):
    password_hash = auth_client.app.state.client_password_hasher.hash("secret123")
    auth_client.app.state.client_postgres_pool.conn.seed_user(type=1, mobile="+15550101111", password=password_hash)

    response = auth_client.post(
        "/auth/login-mobile-password",
        json={"type": 1, "mobile": "+15550101111", "password": "secret123"},
    )

    assert_auth_success(
        response,
        expected_user={"type": 1, "mobile": "+15550101111"},
        app_state=auth_client.app.state,
    )


def test_login_email_otp_uses_seeded_otp_and_creates_missing_user(auth_client):
    auth_client.app.state.client_postgres_pool.conn.seed_otp(otp=123456, email="otp-email@example.com")

    response = auth_client.post(
        "/auth/login-email-otp",
        json={"type": 1, "email": "otp-email@example.com", "otp": 123456},
    )

    assert_auth_success(
        response,
        expected_user={"type": 1, "email": "otp-email@example.com"},
        app_state=auth_client.app.state,
    )
    assert len(auth_client.app.state.client_postgres_pool.conn.users) == 1


def test_login_email_otp_rejects_expired_otp(auth_client):
    auth_client.app.state.client_postgres_pool.conn.seed_otp(
        otp=123456, email="otp-email@example.com", is_valid=False
    )

    response = auth_client.post(
        "/auth/login-email-otp",
        json={"type": 1, "email": "otp-email@example.com", "otp": 123456},
    )

    assert response.status_code == 400
    assert response.json() == {"status": 0, "message": "otp code expired"}


def test_login_mobile_otp_uses_seeded_otp_and_existing_user(auth_client):
    auth_client.app.state.client_postgres_pool.conn.seed_user(type=1, mobile="+15550102222")
    auth_client.app.state.client_postgres_pool.conn.seed_otp(otp=654321, mobile="+15550102222")

    response = auth_client.post(
        "/auth/login-mobile-otp",
        json={"type": 1, "mobile": "+15550102222", "otp": 654321},
    )

    assert_auth_success(
        response,
        expected_user={"type": 1, "mobile": "+15550102222"},
        app_state=auth_client.app.state,
    )
    assert len(auth_client.app.state.client_postgres_pool.conn.users) == 1


def test_login_google_mocks_google_client_and_creates_user(auth_client, monkeypatch):
    def fake_verify_oauth2_token(*, id_token, request, audience):
        assert id_token == "google-token"
        assert audience == auth_client.app.state.config_google_login_client_id
        return {"sub": "google-sub-1", "email": "google@example.com", "name": "Google User"}

    monkeypatch.setattr(auth_router.id_token, "verify_oauth2_token", fake_verify_oauth2_token)

    response = auth_client.post("/auth/login-google", json={"type": 1, "google_token": "google-token"})

    assert_auth_success(
        response,
        expected_user={
            "type": 1,
            "google_login_id": "google-sub-1",
            "email": "google@example.com",
            "name": "Google User",
        },
        app_state=auth_client.app.state,
    )


def test_auth_route_reports_missing_postgres_client(auth_client):
    auth_client.app.state.client_postgres_pool = None

    response = auth_client.post(
        "/auth/login-email-password",
        json={"type": 1, "email": "missing-client@example.com", "password": "secret123"},
    )

    assert response.status_code == 400
    assert response.json()["status"] == 0
    assert "acquire" in response.json()["message"]
