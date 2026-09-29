"""Full HTTP requests through the real app, lifespan included, against a throwaway database.

The app starts from a temporary working directory with test-only environment
variables: config.py loads .env from the working directory and startup resets
./tmp, so running from the repo root would read developer secrets and wipe tmp/.
"""
import io
import json
import os
from contextlib import redirect_stderr
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from tests.integration.support import REPO_ROOT, create_database, drop_database, fetch, requires_postgres

TEST_ENV = {
    "config_token_secret_key": "atom-http-test-secret-key-at-least-32-bytes",
    "config_root_user_password": "root-test-password",
    "config_signup_allowed_roles": "[5]",
    "config_postgres_buffer_flush_auto_sec": "1",
}


@requires_postgres
class HttpIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name, cls.url = create_database()
        cls.workdir = tempfile.TemporaryDirectory()
        cls.previous_cwd = os.getcwd()
        os.chdir(cls.workdir.name)
        cls.env = patch.dict(os.environ, {**TEST_ENV, "config_postgres_url": cls.url})
        cls.env.start()
        # The app prints a traceback for every handled error; these tests trigger 4xx on purpose.
        cls.app_stderr = io.StringIO()
        cls.quiet = redirect_stderr(cls.app_stderr)
        cls.quiet.__enter__()
        for key in [k for k in os.environ if k.lower().startswith("config_") and k not in TEST_ENV and k != "config_postgres_url"]:
            del os.environ[key]
        sys.path.insert(0, str(REPO_ROOT))
        for module in ("main", "config", "config_extend"): sys.modules.pop(module, None)
        import main
        from fastapi.testclient import TestClient
        cls.app = main.app
        cls.client = TestClient(main.app)
        cls.client.__enter__()
        signup = cls.client.post("/auth/signup-username-password", json={"username": "alice", "password": "alice-pass", "role": 5})
        assert signup.status_code == 200, signup.text
        cls.token = signup.json()["message"]["access_token"]
        admin = cls.client.post("/auth/login-username-password", json={"username": "admin", "password": "root-test-password"})
        assert admin.status_code == 200, admin.text
        cls.admin_token = admin.json()["message"]["access_token"]

    @classmethod
    def tearDownClass(cls):
        try:
            cls.client.__exit__(None, None, None)
        finally:
            cls.quiet.__exit__(None, None, None)
            os.chdir(cls.previous_cwd)
            cls.env.stop()
            sys.path.remove(str(REPO_ROOT))
            for module in ("main", "config", "config_extend"): sys.modules.pop(module, None)
            cls.workdir.cleanup()
            drop_database(cls.db_name)

    def auth(self, token=None):
        return {"Authorization": f"Bearer {token or self.token}"}

    def test_app_started_with_test_settings_only(self):
        self.assertEqual(self.app.state.config_postgres_url, self.url)
        self.assertFalse(self.app.state.client_postgres_dict)
        self.assertIsNone(self.app.state.client_redis)
        self.assertTrue(os.path.isdir(os.path.join(self.workdir.name, "tmp")))

    def test_profile_with_token_and_security_headers(self):
        response = self.client.get("/my/profile", headers=self.auth())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["message"]["username"], "alice")
        self.assertNotIn("password", response.json()["message"])
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")

    def test_missing_or_invalid_token_is_401(self):
        for headers, message in [({}, "authorization token missing"), (self.auth("not-a-jwt"), "authentication token invalid")]:
            with self.subTest(message=message):
                response = self.client.get("/my/profile", headers=headers)
                self.assertEqual((response.status_code, response.json()), (401, {"status": 0, "message": message}))

    def test_wrong_password_is_400_invalid_credentials(self):
        response = self.client.post("/auth/login-username-password", json={"username": "alice", "password": "wrong-password"})
        self.assertEqual((response.status_code, response.json()["message"]), (400, "invalid credentials"))

    def test_admin_route_is_403_for_users_and_200_for_root_admin(self):
        denied = self.client.get("/admin/object-read", params={"table": "test"}, headers=self.auth())
        self.assertEqual((denied.status_code, denied.json()["message"]), (403, "access denied"))
        allowed = self.client.get("/admin/object-read", params={"table": "test"}, headers=self.auth(self.admin_token))
        self.assertEqual(allowed.status_code, 200, allowed.text)

    def test_create_then_read_own_objects(self):
        created = self.client.post("/my/object-create", params={"table": "test"}, json={"title": "from http"}, headers=self.auth())
        self.assertEqual(created.status_code, 200, created.text)
        profile_id = self.client.get("/my/profile", headers=self.auth()).json()["message"]["id"]
        read = self.client.get("/my/object-read", params={"table": "test", "filter": json.dumps(["title = from http"])}, headers=self.auth())
        self.assertEqual(read.status_code, 200, read.text)
        rows = read.json()["message"]["obj_list"]
        self.assertEqual([(r["title"], r["created_by_id"]) for r in rows], [("from http", profile_id)])
        self.assertFalse(read.json()["message"]["has_more"])

    def test_no_response_ever_contains_a_password_hash(self):
        def keys(value):
            if isinstance(value, dict): return set(value) | {k for v in value.values() for k in keys(v)}
            if isinstance(value, list): return {k for v in value for k in keys(v)}
            return set()
        self.client.post("/my/object-create", params={"table": "test"}, json={"title": "owned by alice"}, headers=self.auth())
        user_relation = json.dumps(["created_by_id,users,id,fetch|1,*"])
        for label, method, path, params, token in [
            ("profile", "get", "/my/profile", {}, self.token),
            ("users list", "get", "/private/users-list", {}, self.token),
            ("admin read users", "get", "/admin/object-read", {"table": "users"}, self.admin_token),
            ("admin read users, all columns", "get", "/admin/object-read", {"table": "users", "column": "*"}, self.admin_token),
            ("admin read with users relation", "get", "/admin/object-read", {"table": "test", "relation": user_relation}, self.admin_token),
            ("my read with users relation", "get", "/my/object-read", {"table": "test", "relation": user_relation}, self.token),
            ("distinct password", "get", "/admin/table-column-distinct", {"table": "users", "col": "password"}, self.admin_token),
            ("group by password", "get", "/admin/table-column-groupby", {"table": "users", "col": json.dumps(["password"])}, self.admin_token),
            ("max of password", "get", "/admin/table-column-groupby", {"table": "users", "col": json.dumps(["role"]), "agg": "max", "agg_col": "password"}, self.admin_token),
            ("filter on password", "get", "/admin/object-read", {"table": "users", "filter": json.dumps(["password is not null"])}, self.admin_token),
        ]:
            with self.subTest(label):
                response = getattr(self.client, method)(path, params=params, headers=self.auth(token))
                self.assertNotIn("$argon2", response.text)
                self.assertNotIn("password", keys(response.json()))

    def test_malformed_filter_is_400(self):
        response = self.client.get("/my/object-read", params={"table": "test", "filter": json.dumps(["title"])}, headers=self.auth())
        self.assertEqual((response.status_code, response.json()["message"]), (400, "invalid filter: title"))

    def test_public_read_is_served_from_cache_the_second_time(self):
        params = {"table": "test", "order": "id desc"}
        first, second = self.client.get("/public/object-read", params=params), self.client.get("/public/object-read", params=params)
        self.assertEqual((first.status_code, second.status_code), (200, 200))
        self.assertNotEqual(first.headers.get("x-cache"), "hit")
        self.assertEqual(second.headers.get("x-cache"), "hit")
        self.assertEqual(first.json(), second.json())

    def test_rate_limit_returns_429(self):
        statuses = [self.client.post("/public/password-hash", json={"password": "x"}).status_code for _ in range(6)]
        self.assertEqual(statuses, [200] * 5 + [429])

    def test_rate_limit_and_log_use_the_forwarded_client_ip_behind_a_private_proxy(self):
        from fastapi.testclient import TestClient
        proxy = TestClient(self.app, client=("10.0.0.4", 50000))    # like Azure App Service's front end
        direct = TestClient(self.app, client=("5.6.7.8", 50000))    # public client reaching the app directly
        hash_as = lambda client, forwarded: client.post("/public/password-hash", json={"password": "x"}, headers={"X-Forwarded-For": forwarded}).status_code
        self.assertEqual([hash_as(proxy, "49.36.10.5:54321") for _ in range(6)], [200] * 5 + [429])
        self.assertEqual(hash_as(proxy, "103.21.4.9:1234"), 200)     # another user keeps their own limit
        self.assertEqual([hash_as(direct, f"9.9.9.{i}") for i in range(6)], [200] * 5 + [429])   # fake headers do not help
        deadline, rows = time.time() + 10, []
        while time.time() < deadline and not rows:
            rows = fetch(self.url, "SELECT ip_address FROM log_api WHERE ip_address = '49.36.10.5' LIMIT 1")
            time.sleep(0.5)
        self.assertEqual(rows, [{"ip_address": "49.36.10.5"}])

    def test_requests_are_written_to_log_api(self):
        self.client.get("/my/profile", headers=self.auth())
        self.client.get("/my/profile")
        deadline, rows = time.time() + 10, []
        while time.time() < deadline:
            rows = fetch(self.url, "SELECT status_code, response_type FROM log_api WHERE path = '/my/profile'")
            if {200, 401} <= {r["status_code"] for r in rows}: break
            time.sleep(0.5)
        self.assertTrue({200, 401} <= {r["status_code"] for r in rows}, rows)
        self.assertIn("error", {r["response_type"] for r in rows})


if __name__ == "__main__":
    unittest.main()
