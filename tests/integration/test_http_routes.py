"""HTTP coverage for the remaining routes: permissions, CRUD, messages, admin tools, auth, missing services.

Same real-app boot as test_http.py (support.app_start), against a throwaway database.
"""
import csv
import gc
import io
import json
import time
import unittest
import warnings
from contextlib import redirect_stdout

from fastapi.routing import APIRoute

from tests.integration.support import REPO_ROOT
from tests.integration.support import app_login
from tests.integration.support import app_start
from tests.integration.support import app_stop
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import fetch
from tests.integration.support import requires_postgres

FILE = ("rows.csv", b"key\n1\n", "text/csv")

# Routes that need a service the test app does not configure: (method, path, request kwargs, expected 500 message).
MISSING_SERVICE_ROUTES = [
    ("post", "/admin/blob-container-sas", {"params": {"service": "azure", "container": "c"}}, "blob client not initialized"),
    ("post", "/admin/blob-preview-urls", {"json": {"service": "s3", "urls": ["https://b.s3.amazonaws.com/x"]}}, "blob client not initialized"),
    ("get", "/admin/blob-container-read", {"params": {"service": "s3"}}, "blob client not initialized"),
    ("post", "/admin/blob-container-ops", {"params": {"service": "s3", "container": "c", "mode": "create"}}, "blob client not initialized"),
    ("post", "/admin/blob-delete-url", {"json": {"service": "s3", "url": ["https://b.s3.amazonaws.com/x"]}}, "blob client not initialized"),
    ("post", "/admin/mongodb-import", {"data": {"mode": "create", "database": "d", "table": "t"}, "files": {"file": FILE}}, "mongodb client not initialized"),
    ("post", "/admin/postgres-query-generator-ai", {"json": {"question": "count users"}}, "Gemini client not initialized"),
    ("post", "/admin/mssql-query-runner-write", {"json": {"sql": "select 1"}}, "MSSQL client not initialized"),
    ("post", "/admin/mssql-query-runner-read", {"json": {"sql": "select 1"}}, "MSSQL client not initialized"),
    ("post", "/admin/mssql-query-runner-read-export", {"json": {"sql": "select 1"}}, "MSSQL client not initialized"),
    ("post", "/admin/clickhouse-query-runner-write", {"json": {"sql": "select 1"}}, "clickhouse client not initialized"),
    ("post", "/admin/clickhouse-query-runner-read", {"json": {"sql": "select 1"}}, "clickhouse client not initialized"),
    ("post", "/admin/clickhouse-query-runner-read-export", {"json": {"sql": "select 1"}}, "clickhouse client not initialized"),
    ("post", "/admin/clickhouse-query-generator-ai", {"json": {"question": "q"}}, "clickhouse client not initialized"),
    ("post", "/my/object-create-mongodb", {"params": {"database": "d", "table": "t"}, "json": {"a": 1}}, "mongodb client not initialized"),
    ("post", "/my/blob-preview-urls", {"json": {"service": "s3", "urls": ["x"]}}, "blob client not initialized"),
    ("post", "/my/blob-delete-url", {"json": {"service": "s3", "url": ["x"]}}, "blob client not initialized"),
    ("post", "/my/object-create", {"params": {"table": "test", "queue": "redis"}, "json": {"title": "queued"}}, "redis producer not initialized"),
    ("post", "/private/send-email", {"json": {"service": "ses", "sender": "a@b.test", "to": ["x@y.test"], "subject": "s", "text": "t"}}, "email client not initialized"),
    ("post", "/private/blob-upload-file", {"data": {"service": "s3", "container": "c"}, "files": {"file": FILE}}, "required postgres/blob client not initialized"),
    ("post", "/private/blob-upload-presigned", {"params": {"service": "s3", "container": "c"}}, "required postgres/blob client not initialized"),
    ("post", "/public/otp-send-email", {"params": {"service": "ses", "sender": "a@b.test", "email": "x@y.test"}}, "SES client not initialized"),
    ("post", "/public/otp-send-mobile", {"params": {"service": "sns", "mobile": "+911234567890"}}, "SNS client not initialized"),
    ("post", "/public/otp-send-mobile-sns-template", {"json": {"mobile": "+911234567890", "message": "m", "template_id": "t", "entity_id": "e", "sender_id": "s"}}, "SNS client not initialized"),
    ("post", "/auth/login-password", {"json": {"password": "x"}}, "config_login_password not configured"),
]


@requires_postgres
class HttpRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name, cls.url = create_database()
        # "/" serves config_root_html_path, which is relative to the working directory; the test app runs from a temp dir
        cls.handle = app_start(env={"config_postgres_url_master": cls.url, "config_root_html_path": str(REPO_ROOT / "static" / "home.html")})
        cls.app, cls.client = cls.handle["app"], cls.handle["client"]
        cls.admin = app_login(cls.client, path="/auth/login-username-password", body={"username": "admin", "password": "root-test-password"})
        cls.alice = app_login(cls.client, path="/auth/signup-username-password", body={"username": "alice", "password": "alice-pass", "role": 5})
        cls.bob = app_login(cls.client, path="/auth/signup-username-password", body={"username": "bob", "password": "bob-pass", "role": 5})
        cls.alice_id = cls.client.get("/my/profile", headers=cls.auth(cls.alice)).json()["message"]["id"]
        cls.bob_id = cls.client.get("/my/profile", headers=cls.auth(cls.bob)).json()["message"]["id"]

    @classmethod
    def tearDownClass(cls):
        try: app_stop(cls.handle)
        finally: drop_database(cls.db_name)

    @staticmethod
    def auth(token):
        return {"Authorization": f"Bearer {token}"}

    def message(self, response, status=200):
        self.assertEqual(response.status_code, status, response.text)
        return response.json()["message"]

    # 1. admin permission matrix
    def test_every_admin_route_is_401_without_token_and_403_for_users(self):
        admin_routes = [(route.path, method.lower()) for route in self.app.state.func_app_route_list(app=self.app) if isinstance(route, APIRoute) and route.path.startswith("/admin/") for method in route.methods]
        self.assertGreater(len(admin_routes), 20)
        for path, method in admin_routes:
            with self.subTest(path=path):
                anonymous = getattr(self.client, method)(path)
                self.assertEqual(anonymous.status_code, 401, anonymous.text)
                user = getattr(self.client, method)(path, headers=self.auth(self.alice))
                self.assertEqual((user.status_code, user.json()["message"]), (403, "access denied"))

    # 2. CRUD lifecycle and ownership
    def test_my_crud_lifecycle_and_ownership(self):
        [row_id] = self.message(self.client.post("/my/object-create", params={"table": "test"}, json={"title": "mine"}, headers=self.auth(self.alice)))
        self.assertEqual(self.message(self.client.put("/my/object-update", params={"table": "test"}, json={"id": row_id, "title": "hacked"}, headers=self.auth(self.bob))), [])
        self.assertEqual(self.message(self.client.post("/my/object-delete", json={"table": "test", "ids": [row_id]}, headers=self.auth(self.bob))), "0 ids deleted")
        self.assertEqual(fetch(self.url, "SELECT title FROM test WHERE id = $1", row_id), [{"title": "mine"}])
        self.assertEqual(self.message(self.client.put("/my/object-update", params={"table": "test"}, json={"id": row_id, "title": "edited"}, headers=self.auth(self.alice))), [row_id])
        read = self.message(self.client.get("/my/object-read", params={"table": "test", "filter": json.dumps([f"id = {row_id}"])}, headers=self.auth(self.alice)))
        self.assertEqual([(r["title"], r["updated_by_id"]) for r in read["obj_list"]], [("edited", self.alice_id)])
        self.assertEqual(self.message(self.client.post("/my/object-delete", json={"table": "test", "ids": [row_id]}, headers=self.auth(self.alice))), "1 ids deleted")

    def test_object_read_export_streams_only_the_callers_rows_as_csv(self):
        self.client.post("/my/object-create", params={"table": "test"}, json={"obj_list": [{"title": "alice-export-1"}, {"title": "=HYPERLINK(1)"}]}, headers=self.auth(self.alice))
        self.client.post("/my/object-create", params={"table": "test"}, json={"title": "bob-export"}, headers=self.auth(self.bob))
        response = self.client.get("/my/object-read-export", params={"table": "test", "column": "id,title,created_by_id"}, headers=self.auth(self.alice))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["content-type"].split(";")[0], "text/csv")
        self.assertIn('filename="test.csv"', response.headers["content-disposition"])
        rows = list(csv.DictReader(io.StringIO(response.text)))
        titles = {r["title"] for r in rows}
        self.assertIn("alice-export-1", titles)
        self.assertIn("'=HYPERLINK(1)", titles)    # spreadsheet formulas are neutralised
        self.assertNotIn("bob-export", titles)
        self.assertEqual({r["created_by_id"] for r in rows}, {str(self.alice_id)})

    def test_object_read_export_rejects_bad_input_before_streaming(self):
        self.assertEqual(self.client.get("/my/object-read-export", params={"table": "test"}).status_code, 401)
        self.assertEqual(self.message(self.client.get("/my/object-read-export", params={"table": "users"}, headers=self.auth(self.alice)), 400), "read disabled for table: users")
        self.assertEqual(self.message(self.client.get("/my/object-read-export", params={"table": "test", "limit": 5}, headers=self.auth(self.alice)), 400), "request contains unknown parameters")
        self.assertEqual(self.client.get("/my/object-read-export", params={"table": "test", "column": "password"}, headers=self.auth(self.alice)).status_code, 400)

    def test_public_private_admin_exports_follow_their_read_rules(self):
        self.client.post("/my/object-create", params={"table": "test"}, json={"title": "shared-export"}, headers=self.auth(self.alice))
        csv_rows = lambda response: list(csv.DictReader(io.StringIO(response.text)))
        public = self.client.get("/public/object-read-export", params={"table": "test", "column": "id,title"})
        self.assertEqual(public.status_code, 200, public.text)
        self.assertIn("shared-export", {r["title"] for r in csv_rows(public)})
        self.assertEqual(self.message(self.client.get("/public/object-read-export", params={"table": "users"}), 400), "read disabled for table: users")
        self.assertEqual(self.client.get("/private/object-read-export", params={"table": "test"}).status_code, 401)
        private = self.client.get("/private/object-read-export", params={"table": "test", "column": "id,title"}, headers=self.auth(self.bob))
        self.assertIn("shared-export", {r["title"] for r in csv_rows(private)})
        self.assertEqual(self.client.get("/admin/object-read-export", params={"table": "users"}, headers=self.auth(self.alice)).status_code, 403)
        admin = self.client.get("/admin/object-read-export", params={"table": "users"}, headers=self.auth(self.admin))
        self.assertEqual(admin.status_code, 200, admin.text)
        header = admin.text.splitlines()[0].split(",")
        self.assertIn("username", header)
        self.assertNotIn("password", header)    # blocked columns never leave, even for admins

    def test_my_delete_all_only_removes_own_rows(self):
        self.client.post("/my/object-create", params={"table": "test"}, json={"obj_list": [{"title": "bob-1"}, {"title": "bob-2"}]}, headers=self.auth(self.bob))
        self.client.post("/my/object-create", params={"table": "test"}, json={"title": "alice-keeps"}, headers=self.auth(self.alice))
        result = self.message(self.client.delete("/my/object-delete-all", params={"table": "test"}, headers=self.auth(self.bob)))
        self.assertEqual((result["deleted_count"], result["has_more"]), (2, False))
        self.assertEqual(fetch(self.url, "SELECT count(*) AS n FROM test WHERE created_by_id = $1", self.bob_id), [{"n": 0}])
        self.assertEqual(fetch(self.url, "SELECT count(*) AS n FROM test WHERE title = 'alice-keeps'"), [{"n": 1}])

    def test_admin_crud_lifecycle(self):
        [row_id] = self.message(self.client.post("/admin/object-create", params={"table": "test"}, json={"title": "by admin"}, headers=self.auth(self.admin)))
        self.assertEqual(self.message(self.client.put("/admin/object-update", params={"table": "test"}, json={"id": row_id, "title": "admin edit"}, headers=self.auth(self.admin))), [row_id])
        self.assertEqual(fetch(self.url, "SELECT title FROM test WHERE id = $1", row_id), [{"title": "admin edit"}])
        self.assertEqual(self.message(self.client.post("/admin/object-delete", json={"table": "test", "ids": [row_id]}, headers=self.auth(self.admin))), "1 ids deleted")

    def test_public_and_private_reads_respect_table_allowlists(self):
        self.message(self.client.post("/public/object-create", params={"table": "test"}, json={"title": "public row"}))
        self.assertEqual(self.message(self.client.post("/public/object-create", params={"table": "task"}, json={"title": "x"}), 400), "creation disabled for table: task")
        titles = [r["title"] for r in self.message(self.client.get("/private/object-read", params={"table": "test"}, headers=self.auth(self.alice)))["obj_list"]]
        self.assertIn("public row", titles)
        self.assertEqual(self.message(self.client.get("/private/object-read", params={"table": "users"}, headers=self.auth(self.alice)), 400), "read disabled for table: users")
        users = self.message(self.client.get("/private/users-list", headers=self.auth(self.alice)))["obj_list"]
        self.assertTrue({"alice", "bob"} <= {u["username"] for u in users})
        self.assertNotIn("password", {k for u in users for k in u})

    def test_users_list_optional_role_and_pagination(self):
        def users(**params):
            return self.message(self.client.get("/private/users-list", params=params, headers=self.auth(self.alice)))

        expected_role_users = fetch(self.url, "SELECT id, username FROM users WHERE role = 5 ORDER BY id")
        self.assertEqual(sorted(users(role=5)["obj_list"], key=lambda user: user["id"]), expected_role_users)
        self.assertEqual([u["username"] for u in users(role=1)["obj_list"]], ["admin"])
        self.assertEqual(users(role=20), {"obj_list": [], "has_next_page": False})
        all_users = users(limit=1000)["obj_list"]
        self.assertEqual({u["id"] for u in all_users}, {u["id"] for u in fetch(self.url, "SELECT id FROM users")})
        self.assertTrue({"admin", "alice", "bob"} <= {u["username"] for u in all_users})
        # One page boundary verifies pagination without relying on the order of
        # extra accounts that share a NULL username in this class's fixture.
        for page in (1, 2):
            result = users(limit=1, page=page)
            self.assertEqual(result["obj_list"], all_users[page-1:page])
            self.assertTrue(result["has_next_page"])
        self.assertEqual(users(limit=1, page=len(all_users)+1), {"obj_list": [], "has_next_page": False})
        self.message(self.client.get("/private/users-list", params={"role": "invalid"}, headers=self.auth(self.alice)), 400)

    def test_groupby_and_distinct_on_public_and_private(self):
        self.message(self.client.post("/public/object-create", params={"table": "test"}, json={"obj_list": [{"title": "grouped"}, {"title": "grouped"}]}))
        filter_grouped = json.dumps(["title = grouped"])
        for scope, headers in (("public", {}), ("private", self.auth(self.alice))):
            with self.subTest(scope=scope):
                groupby = self.message(self.client.get(f"/{scope}/table-column-groupby", params={"table": "test", "col": json.dumps(["title"]), "filter": filter_grouped}, headers=headers))
                self.assertEqual(groupby["obj_list"], [{"title": "grouped", "count": 2}])
                distinct = self.message(self.client.get(f"/{scope}/table-column-distinct", params={"table": "test", "col": "title", "filter": filter_grouped}, headers=headers))
                self.assertEqual(distinct["item_list"], ["grouped"])

    # 3. messages
    def test_message_inbox_thread_and_mark_read(self):
        self.message(self.client.post("/my/object-create", params={"table": "message"}, json={"received_by_id": self.bob_id, "description": "hi bob"}, headers=self.auth(self.alice)))
        unread = self.message(self.client.get("/my/message-inbox", params={"mode": "unread"}, headers=self.auth(self.bob)))["obj_list"]
        self.assertEqual([m["description"] for m in unread], ["hi bob"])
        thread = self.message(self.client.get("/my/message-thread", params={"user_id": self.alice_id}, headers=self.auth(self.bob)))["obj_list"]
        self.assertEqual([m["description"] for m in thread], ["hi bob"])
        self.assertEqual(self.message(self.client.get("/my/message-inbox", params={"mode": "unread"}, headers=self.auth(self.bob)))["obj_list"], [])
        self.assertEqual(fetch(self.url, "SELECT read_at IS NOT NULL AS is_read FROM message WHERE description = 'hi bob'"), [{"is_read": True}])

    # 4. postgres admin tools
    def test_postgres_query_runners(self):
        self.assertEqual(self.message(self.client.post("/admin/postgres-query-runner-read", json={"sql": "SELECT count(*) AS n FROM users WHERE username = 'alice'"}, headers=self.auth(self.admin))), [{"n": 1}])
        self.assertEqual(self.message(self.client.post("/admin/postgres-query-runner-read", json={"sql": "DELETE FROM test"}, headers=self.auth(self.admin)), 400), "Only SELECT/WITH queries are supported")
        export = self.client.post("/admin/postgres-query-runner-read-export", json={"sql": "SELECT username FROM users WHERE username IN ('alice', 'bob') ORDER BY username"}, headers=self.auth(self.admin))
        self.assertEqual((export.status_code, export.headers["content-type"].split(";")[0]), (200, "text/csv"))
        self.assertEqual(export.text.split(), ["username", "alice", "bob"])
        self.message(self.client.post("/public/object-create", params={"table": "test"}, json={"title": "runner target"}))
        self.assertEqual(self.message(self.client.post("/admin/postgres-query-runner-write", json={"sql": "UPDATE test SET title = 'runner wrote' WHERE title = 'runner target'"}, headers=self.auth(self.admin))), "UPDATE 1")

    def test_postgres_info_schema_and_sync(self):
        info = self.message(self.client.get("/admin/postgres-info", headers=self.auth(self.admin)))
        self.assertEqual(info["database_name"], self.db_name)
        self.assertIn("users", self.message(self.client.get("/admin/postgres-schema", headers=self.auth(self.admin))))
        self.assertEqual(self.message(self.client.get("/admin/sync", headers=self.auth(self.admin))), "done")

    # 5. auth variants
    def test_email_mobile_and_id_ext_password_logins(self):
        fetch(self.url, "UPDATE users SET email = 'alice@example.test', mobile = '+910000000001', id_ext = 'ext-alice' WHERE id = $1", self.alice_id)
        for path, field, value in (("/auth/login-email-password", "email", "alice@example.test"), ("/auth/login-mobile-password", "mobile", "+910000000001"), ("/auth/login-id-ext-password", "id_ext", "ext-alice")):
            with self.subTest(path=path):
                token = self.message(self.client.post(path, json={field: value, "password": "alice-pass"}))["access_token"]
                self.assertEqual(self.message(self.client.get("/my/profile", headers=self.auth(token)))["id"], self.alice_id)
                self.assertEqual(self.message(self.client.post(path, json={field: value, "password": "wrong-pass"}), 400), "invalid credentials")

    def test_otp_verify_and_otp_logins(self):
        # otp rows are inserted directly, as the send routes would after delivering the code
        fetch(self.url, "INSERT INTO otp (otp, email) VALUES (111111, 'verify@example.test')")
        self.assertEqual(self.message(self.client.get("/public/otp-verify", params={"type": "email", "value": "verify@example.test", "otp": 222222}), 400), "invalid otp code")
        self.assertEqual(self.message(self.client.get("/public/otp-verify", params={"type": "email", "value": "verify@example.test", "otp": 111111})), "done")
        fetch(self.url, "INSERT INTO otp (otp, email) VALUES (333333, 'otp-user@example.test')")
        email_token = self.message(self.client.post("/auth/login-email-otp", json={"email": "otp-user@example.test", "otp": 333333, "role": 5}))["access_token"]
        self.assertEqual(self.message(self.client.get("/my/profile", headers=self.auth(email_token)))["email"], "otp-user@example.test")
        fetch(self.url, "INSERT INTO otp (otp, mobile) VALUES (444444, '+910000000099')")
        mobile_token = self.message(self.client.post("/auth/login-mobile-otp", json={"mobile": "+910000000099", "otp": 444444, "role": 5}))["access_token"]
        self.assertEqual(self.message(self.client.get("/my/profile", headers=self.auth(mobile_token)))["mobile"], "+910000000099")
        self.assertEqual(fetch(self.url, "SELECT count(*) AS n FROM otp WHERE otp IN (111111, 333333, 444444)"), [{"n": 0}])    # used codes are deleted

    def test_token_refresh_needs_the_refresh_token(self):
        tokens = self.message(self.client.post("/auth/login-username-password", json={"username": "bob", "password": "bob-pass"}))
        self.assertEqual(self.message(self.client.post("/my/token-refresh", headers=self.auth(tokens["access_token"])), 401), "refresh token required")
        refreshed = self.message(self.client.post("/my/token-refresh", headers=self.auth(tokens["refresh_token"])))
        self.assertEqual(self.message(self.client.get("/my/profile", headers=self.auth(refreshed["access_token"])))["id"], self.bob_id)

    # 6. missing external services
    def test_routes_needing_unconfigured_services_return_500(self):
        for method, path, kwargs, expected in MISSING_SERVICE_ROUTES:
            token = self.admin if path.startswith("/admin/") else self.alice
            with self.subTest(path=path):
                response = getattr(self.client, method)(path, headers=self.auth(token), **kwargs)
                self.assertEqual((response.status_code, response.json()["message"]), (500, expected))

    def test_failed_otp_send_stores_no_code(self):
        response = self.client.post("/public/otp-send-email", params={"service": "ses", "sender": "a@b.test", "email": "never-sent@example.test"})
        self.assertEqual(response.status_code, 500, response.text)
        self.assertEqual(fetch(self.url, "SELECT count(*) AS n FROM otp WHERE email = 'never-sent@example.test'"), [{"n": 0}])

    def test_upload_temp_files_are_closed_after_the_request(self):
        def unclosed_files(call):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ResourceWarning)
                call()
                gc.collect()
            return [str(w.message) for w in caught if "Unclosed file" in str(w.message)]
        upload = lambda table: self.client.post("/admin/postgres-import", data={"mode": "create", "table": table}, files={"file": ("rows.csv", b"title\nimported\n", "text/csv")}, headers=self.auth(self.admin))
        self.assertEqual(unclosed_files(lambda: self.assertEqual(upload("test").status_code, 200)), [])
        self.assertEqual(unclosed_files(lambda: self.assertEqual(upload("missing_table").status_code, 400)), [])
        self.assertEqual(fetch(self.url, "SELECT count(*) AS n FROM test WHERE title = 'imported'"), [{"n": 1}])

    # background mode
    def wait_for_rows(self, sql):
        deadline, rows = time.time() + 5, []
        while time.time() < deadline and not rows:
            rows = fetch(self.url, sql)
            time.sleep(0.1)
        return rows

    def test_background_request_returns_202_and_runs_later(self):
        response = self.client.post("/my/object-create", params={"table": "test", "is_background": "true"}, json={"title": "created in background"}, headers=self.auth(self.alice))
        self.assertEqual(self.message(response, 202), "added in background")
        self.assertEqual(self.wait_for_rows("SELECT created_by_id FROM test WHERE title = 'created in background'"), [{"created_by_id": self.alice_id}])

    def test_background_upload_runs_and_closes_its_temp_files(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            response = self.client.post("/admin/postgres-import", params={"is_background": "true"}, data={"mode": "create", "table": "test"}, files={"file": ("rows.csv", b"title\nimported in background\n", "text/csv")}, headers=self.auth(self.admin))
            self.assertEqual(self.message(response, 202), "added in background")
            self.assertEqual(len(self.wait_for_rows("SELECT id FROM test WHERE title = 'imported in background'")), 1)
            gc.collect()
        self.assertEqual([str(w.message) for w in caught if "Unclosed file" in str(w.message)], [])

    def test_monitor_is_admin_only_and_traces_on_demand(self):
        self.assertEqual(self.client.get("/admin/monitor").status_code, 401)
        self.assertEqual(self.client.get("/admin/monitor", headers=self.auth(self.alice)).status_code, 403)
        report = self.message(self.client.get("/admin/monitor", headers=self.auth(self.admin)))    # view=memory by default
        self.assertGreater(report["process"]["rss_bytes"], 0)
        names = {item["name"] for item in report["app_state"]}
        self.assertIn("cache_users_role", names)
        self.assertFalse(any(name.startswith(("func_", "client_")) for name in names))    # functions are skipped, clients only counted
        self.assertNotIn("clients", report)    # clients are listed once, in the app view
        memory = lambda **params: self.message(self.client.get("/admin/monitor", params=params, headers=self.auth(self.admin)))
        self.assertTrue(memory(trace="start")["trace"]["is_tracing"])
        self.assertTrue(memory()["trace"]["is_tracing"])    # still on until stopped (or 5 minutes)
        self.assertFalse(memory(trace="stop")["trace"]["is_tracing"])
        self.assertEqual(self.client.get("/admin/monitor", params={"trace": "forever"}, headers=self.auth(self.admin)).status_code, 400)

    def test_monitor_views(self):
        view = lambda name, **params: self.message(self.client.get("/admin/monitor", params={"view": name, **params}, headers=self.auth(self.admin)))
        requests = view("requests", hours=1)
        self.assertTrue(requests["is_enabled"])
        self.assertEqual(len(requests["timeline"]), 61)    # one bucket per minute, quiet minutes as zero
        self.assertIn("p95_ms", requests["totals"])
        errors = view("errors", hours=168)
        self.assertNotIn("background", errors)    # background counters are listed once, in the background view
        database = view("database")
        self.assertGreater(database["info"]["size_bytes"], 0)
        self.assertTrue(database["info"]["user_name"])
        self.assertEqual([pool["name"] for pool in database["pools"] if pool["is_log_api"]], ["master"])
        self.assertIn("master", {pool["name"] for pool in database["pools"]})
        self.assertIn("users", {table["name"].split(".")[-1] for table in database["tables"]})
        self.assertEqual(self.client.get("/admin/monitor", params={"view": "database", "connection": "missing"}, headers=self.auth(self.admin)).status_code, 404)    # unknown connection: 404, as on every route
        background = view("background")
        self.assertIn("Buffer flush", {task["name"] for task in background["tasks"]})
        self.assertIn("log_api_write", {item["name"] for item in background["errors"]})
        app = self.client.get("/admin/monitor", params={"view": "app"}, headers=self.auth(self.admin))
        config = {item["name"]: item["value"] for item in self.message(app)["config"]}
        self.assertIn("client_postgres_dict", {client["name"] for client in self.message(app)["clients"]})
        self.assertEqual(config["config_postgres_url_dict"], "set")    # secrets and URLs are masked
        self.assertNotIn("postgresql://", app.text)
        self.assertEqual(self.client.get("/admin/monitor", params={"view": "secrets"}, headers=self.auth(self.admin)).status_code, 400)
        self.assertEqual(self.client.get("/admin/monitor", params={"view": "requests", "hours": 5}, headers=self.auth(self.admin)).status_code, 400)

    def runtime_status(self):
        """This worker's background error counters and buffered rows, from the monitor's background view."""
        background = self.message(self.client.get("/admin/monitor", params={"view": "background"}, headers=self.auth(self.admin)))
        rows = lambda name: sum(item["rows"] for item in background["buffers"] if item["buffer"] == name)
        return {"error_count": {item["name"]: item["count"] for item in background["errors"]}, "buffer_rows_pending": {"create": rows("create"), "log_api": rows("log_api")}}

    def test_log_database_outage_is_counted_buffered_and_recovered(self):
        before = self.runtime_status()["error_count"]
        requests_sent = self.client.app.state.config_table["log_api"]["buffer_limit"] + 5    # enough to fill the buffer, so a request writes too
        health_logged = lambda: fetch(self.url, "SELECT count(*) AS n FROM log_api WHERE path = '/health'")[0]["n"]
        time.sleep(1.2)    # let earlier requests flush so the baseline is complete
        logged_before = health_logged()
        fetch(self.url, "ALTER TABLE log_api RENAME TO log_api_offline")
        try:
            with redirect_stdout(io.StringIO()):
                self.assertEqual({self.client.get("/health").status_code for _ in range(requests_sent)}, {200})    # the API keeps answering
                time.sleep(1.5)    # at least one periodic flush attempt (config_postgres_buffer_flush_auto_sec=1)
                during = self.runtime_status()
        finally:
            fetch(self.url, "ALTER TABLE log_api_offline RENAME TO log_api")
        self.assertGreater(during["error_count"]["log_api_write"], before["log_api_write"])
        self.assertGreater(during["error_count"]["buffer_flush"], before["buffer_flush"])
        self.assertGreater(during["buffer_rows_pending"]["log_api"], 0)    # rows wait in memory instead of being lost
        deadline, logged = time.time() + 5, 0
        while time.time() < deadline and logged < logged_before + requests_sent:
            logged = health_logged()
            time.sleep(0.2)
        self.assertGreaterEqual(logged, logged_before + requests_sent)    # the outage's rows are written once the table is back

    def test_background_error_is_logged_with_its_type(self):
        count_before = self.runtime_status()["error_count"]["background_task"]
        log = io.StringIO()
        with redirect_stdout(log):
            response = self.client.post("/my/object-create", params={"table": "no_such_table", "is_background": "true"}, json={"title": "x"}, headers=self.auth(self.alice))
            self.assertEqual(response.status_code, 202, response.text)
            deadline = time.time() + 5
            while time.time() < deadline and "background_task error" not in log.getvalue(): time.sleep(0.05)
        self.assertIn("background_task error #", log.getvalue())
        self.assertIn("Exception(\"table 'no_such_table' not found\")", log.getvalue())
        self.assertEqual(self.runtime_status()["error_count"]["background_task"], count_before + 1)
        self.assertEqual(self.message(self.client.get("/health")), "ok")

    # 7. small routes
    def test_root_health_info_ping_and_converter(self):
        root = self.client.get("/")
        self.assertEqual((root.status_code, root.headers["content-type"].split(";")[0]), (200, "text/html"))
        self.assertIn('fetch("/static-pages")', root.text)
        self.assertIsInstance(self.message(self.client.get("/static-pages")), list)    # the app runs from a temp dir, so its static/ is empty
        self.assertEqual(self.message(self.client.get("/health")), "ok")
        self.assertIn("/health", self.message(self.client.get("/info"))["api_list"])
        self.assertEqual(self.message(self.client.post("/my/ping", headers=self.auth(self.alice))), "pong")
        self.assertEqual(fetch(self.url, "SELECT last_active_at IS NOT NULL AS is_set FROM users WHERE id = $1", self.alice_id), [{"is_set": True}])
        encoded = self.message(self.client.get("/public/converter-number", params={"datatype": "int", "mode": "encode", "x": "12345"}))
        self.assertEqual(str(self.message(self.client.get("/public/converter-number", params={"datatype": "int", "mode": "decode", "x": str(encoded)}))), "12345")


if __name__ == "__main__":
    unittest.main()
