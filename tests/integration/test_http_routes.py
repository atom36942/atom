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
    ("post", "/admin/postgres-query-ai", {"json": {"question": "count users"}}, "Gemini client not initialized"),
    ("post", "/admin/mssql-query-runner-write", {"json": {"sql": "select 1"}}, "MSSQL client not initialized"),
    ("post", "/admin/mssql-query-runner-read", {"json": {"sql": "select 1"}}, "MSSQL client not initialized"),
    ("post", "/admin/mssql-query-runner-read-export", {"json": {"sql": "select 1"}}, "MSSQL client not initialized"),
    ("post", "/admin/clickhouse-query-runner-write", {"json": {"sql": "select 1"}}, "clickhouse client not initialized"),
    ("post", "/admin/clickhouse-query-runner-read", {"json": {"sql": "select 1"}}, "clickhouse client not initialized"),
    ("post", "/admin/clickhouse-query-runner-read-export", {"json": {"sql": "select 1"}}, "clickhouse client not initialized"),
    ("post", "/admin/clickhouse-query-ai", {"json": {"question": "q"}}, "clickhouse client not initialized"),
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
        cls.alice = app_login(cls.client, path="/auth/signup-username-password", body={"role": 5, "username": "alice", "password": "alice-pass"})
        cls.bob = app_login(cls.client, path="/auth/signup-username-password", body={"role": 5, "username": "bob", "password": "bob-pass"})
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
                self.assertEqual((user.status_code, user.json()["message"]), (403, "permission denied"))

    def test_admin_routes_root_holds_every_id_others_need_a_grant(self):
        admin_ids = sorted(cfg["id"] for path, cfg in self.app.state.config_api.items() if path.startswith("/admin/"))
        self.assertEqual(fetch(self.url, "SELECT permissions FROM users WHERE id = 1"), [{"permissions": admin_ids}])    # set at startup
        # a role is nothing: another role 1 user without grants is refused
        self.message(self.client.post("/admin/user-create", json={"role": 1, "username": "admin2", "password": "admin2-pass"}, headers=self.auth(self.admin)))
        admin2 = app_login(self.client, path="/auth/login-username-password", body={"username": "admin2", "password": "admin2-pass"})
        self.assertEqual(self.message(self.client.get("/admin/object-read", params={"table": "test"}, headers=self.auth(admin2)), 403), "permission denied")
        # a user granted one route id gets that route only
        [row_id] = self.message(self.client.post("/my/object-create", params={"table": "test"}, json={"title": "alice's"}, headers=self.auth(self.alice)))
        self.message(self.client.put("/admin/user-update", json={"id": self.bob_id, "permissions": [66]}, headers=self.auth(self.admin)))    # /admin/object-update
        self.assertEqual(self.message(self.client.put("/admin/user-update", json={"id": self.bob_id, "permissions": [999]}, headers=self.auth(self.admin)), 400).count("not ids of routes with user_check_permission"), 1)
        bob = app_login(self.client, path="/auth/login-username-password", body={"username": "bob", "password": "bob-pass"})
        self.assertEqual(self.message(self.client.put("/admin/object-update", params={"table": "test"}, json={"id": row_id, "title": "by bob"}, headers=self.auth(bob))), [row_id])
        self.assertEqual(fetch(self.url, "SELECT title, created_by_id, updated_by_id FROM test WHERE id = $1", row_id), [{"title": "by bob", "created_by_id": self.alice_id, "updated_by_id": self.bob_id}])
        self.assertEqual(self.message(self.client.get("/admin/object-read", params={"table": "test"}, headers=self.auth(bob)), 403), "permission denied")    # update only: no read
        self.assertEqual(self.message(self.client.put("/admin/user-update", json={"id": self.alice_id, "city": "Goa"}, headers=self.auth(bob)), 403), "permission denied")
        # revoked: the write route checks live, so the same token stops at once
        self.message(self.client.put("/admin/user-update", json={"id": self.bob_id, "permissions": None}, headers=self.auth(self.admin)))
        self.assertEqual(self.message(self.client.put("/admin/object-update", params={"table": "test"}, json={"id": row_id, "title": "again"}, headers=self.auth(bob)), 403), "permission denied")
        [admin2_id] = [row["id"] for row in fetch(self.url, "SELECT id FROM users WHERE username = 'admin2'")]
        self.message(self.client.put("/admin/user-update", json={"id": admin2_id, "role": 9}, headers=self.auth(self.admin)))    # other tests expect admin as the only role 1 user

    def test_public_create_honeypot(self):
        self.assertEqual(self.message(self.client.post("/public/object-create", params={"table": "test"}, json={"title": "bot", "website": "http://spam.test"}), 400), "refused")    # the hidden honeypot field, filled
        [public_id] = self.message(self.client.post("/public/object-create", params={"table": "test"}, json={"title": "person", "website": ""}))
        self.assertEqual(fetch(self.url, "SELECT title, created_by_id FROM test WHERE id = $1", public_id), [{"title": "person", "created_by_id": None}])    # an empty one is dropped

    def test_admin_user_update_obj_list_is_all_or_nothing(self):
        users = "SELECT id, city, job_title, updated_by_id FROM users WHERE id = ANY($1) ORDER BY id"
        ids = sorted([self.alice_id, self.bob_id])
        body = {"obj_list": [{"id": self.alice_id, "city": "Pune"}, {"id": self.bob_id, "job_title": "Lead"}]}    # different columns per user
        self.assertEqual(self.message(self.client.put("/admin/user-update", json=body, headers=self.auth(self.admin))), "2 users updated")
        self.assertEqual(fetch(self.url, users, ids), sorted([{"id": self.alice_id, "city": "Pune", "job_title": None, "updated_by_id": 1}, {"id": self.bob_id, "city": None, "job_title": "Lead", "updated_by_id": 1}], key=lambda r: r["id"]))
        body = {"obj_list": [{"id": self.alice_id, "city": "Delhi"}, {"id": 999999, "city": "Goa"}]}
        self.assertEqual(self.message(self.client.put("/admin/user-update", json=body, headers=self.auth(self.admin)), 404), "user not found: [999999]")
        self.assertEqual(fetch(self.url, "SELECT city FROM users WHERE id = $1", self.alice_id), [{"city": "Pune"}])    # rolled back
        self.message(self.client.put("/admin/user-update", json={"obj_list": [{"id": self.alice_id, "city": None}, {"id": self.bob_id, "job_title": None}]}, headers=self.auth(self.admin)))

    def test_admin_user_create_takes_other_users_columns_in_one_go(self):
        create = lambda body: self.client.post("/admin/user-create", json={"role": 5, "password": "dave-pass", **body}, headers=self.auth(self.admin))
        for column, value in (("oidc_google", "g1"), ("email", "d@x.io"), ("permissions", [86]), ("created_at", "2026-01-01"), ("verified_at", "2026-01-01"), ("deactivated_at", "2026-01-01"), ("id", 5)):
            with self.subTest(column=column):
                self.assertIn(f"{column} cannot be set when creating a user", self.message(create({"username": "dave", column: value}), 400))
        self.assertIn("does not exist", self.message(create({"username": "dave", "no_such_column": 1}), 400))
        self.assertEqual(fetch(self.url, "SELECT count(*) AS n FROM users WHERE username = 'dave'"), [{"n": 0}])    # nothing half-created
        user_id = self.message(create({"username": "dave", "city": "Pune", "job_title": "Lead"}))["id"]
        self.assertEqual(fetch(self.url, "SELECT role, city, job_title, created_by_id FROM users WHERE id = $1", user_id), [{"role": 5, "city": "Pune", "job_title": "Lead", "created_by_id": 1}])
        self.assertTrue(fetch(self.url, "SELECT password FROM users WHERE id = $1", user_id)[0]["password"].startswith("$argon2"))    # hashed, never stored as sent

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

    def test_object_read_pages_after_the_last_id(self):
        ids = self.message(self.client.post("/my/object-create", params={"table": "test"}, json={"obj_list": [{"title": f"page-{i}"} for i in range(5)]}, headers=self.auth(self.alice)))
        read = lambda **params: self.message(self.client.get("/my/object-read", params={"table": "test", "filter": json.dumps(["title ilike page-%"]), "order": "id desc", "limit": 2, **params}, headers=self.auth(self.alice)))
        seen, after = [], None
        while True:
            page = read(**({"after": after} if after else {}))
            seen += [r["id"] for r in page["obj_list"]]
            if page["after"] is None: break
            after = page["after"]
        self.assertEqual(seen, sorted(ids, reverse=True))    # every row once, newest first, no OFFSET
        self.assertEqual(self.message(self.client.get("/my/object-read", params={"table": "test", "order": "title asc", "after": after}, headers=self.auth(self.alice)), 400), "after does not belong to this list: start from the first page")
        jump = read(page=2)    # page jumps with OFFSET; its after goes on with the cursor
        self.assertEqual([r["id"] for r in jump["obj_list"]], sorted(ids, reverse=True)[2:4])
        self.assertEqual([r["id"] for r in read(after=jump["after"])["obj_list"]], sorted(ids, reverse=True)[4:])
        self.assertEqual(self.message(self.client.get("/my/object-read", params={"table": "test", "page": 2, "after": jump["after"]}, headers=self.auth(self.alice)), 400), "send page or after, not both")
        self.assertEqual(self.message(self.client.get("/my/object-read", params={"table": "test", "limit": 100, "page": 102}, headers=self.auth(self.alice)), 400), "page reaches past 10,000 rows: page on with after")

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
        self.assertEqual(self.message(self.client.get("/my/object-read-export", params={"table": "users"}, headers=self.auth(self.alice)), 403), "my read not allowed for table: users (add \"read\" to \"my\" of users in config_postgres_schema_master)")
        self.assertEqual(self.message(self.client.get("/my/object-read-export", params={"table": "test", "page": 2}, headers=self.auth(self.alice)), 400), "request contains unknown parameters")
        self.assertEqual(self.message(self.client.get("/my/object-read-export", params={"table": "test", "limit": 0}, headers=self.auth(self.alice)), 400), "Rows must be between 1 and 1,000,000.")
        self.assertEqual(self.client.get("/my/object-read-export", params={"table": "test", "column": "password"}, headers=self.auth(self.alice)).status_code, 400)

    def test_public_private_admin_exports_follow_their_read_rules(self):
        self.client.post("/my/object-create", params={"table": "test"}, json={"title": "shared-export"}, headers=self.auth(self.alice))
        csv_rows = lambda response: list(csv.DictReader(io.StringIO(response.text)))
        public = self.client.get("/public/object-read-export", params={"table": "test", "column": "id,title"})
        self.assertEqual(public.status_code, 200, public.text)
        self.assertIn("shared-export", {r["title"] for r in csv_rows(public)})
        self.assertEqual(self.message(self.client.get("/public/object-read-export", params={"table": "users"}), 403), "public read not allowed for table: users (add \"read\" to \"public\" of users in config_postgres_schema_master)")
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
        self.assertEqual(self.message(self.client.post("/public/object-create", params={"table": "task"}, json={"title": "x"}), 403), "public create not allowed for table: task (add \"create\" to \"public\" of task in config_postgres_schema_master)")
        titles = [r["title"] for r in self.message(self.client.get("/private/object-read", params={"table": "test"}, headers=self.auth(self.alice)))["obj_list"]]
        self.assertIn("public row", titles)
        self.assertEqual(self.message(self.client.get("/private/object-read", params={"table": "users"}, headers=self.auth(self.alice)), 403), "private read not allowed for table: users (add \"read\" to \"private\" of users in config_postgres_schema_master)")
        users = self.message(self.client.get("/private/user-read", headers=self.auth(self.alice)))["obj_list"]
        self.assertTrue({"alice", "bob"} <= {u["username"] for u in users})
        self.assertEqual({k for u in users for k in u}, {"id", "username", "name", "role", "permissions", "created_at", "deactivated_at"})

    def test_user_read_filters_pages_and_blocks_other_columns(self):
        def users(**params):
            return self.message(self.client.get("/private/user-read", params={key: json.dumps(value) if key == "filter" else value for key, value in params.items()}, headers=self.auth(self.alice)))

        expected_role_users = fetch(self.url, "SELECT id, username FROM users WHERE role = 5 ORDER BY id")
        self.assertEqual(sorted(({"id": u["id"], "username": u["username"]} for u in users(filter=["role = 5"])["obj_list"]), key=lambda user: user["id"]), expected_role_users)
        self.assertEqual([u["username"] for u in users(filter=["role = 1"])["obj_list"]], ["admin"])
        self.assertEqual({u["id"] for u in users(filter=["role in 1,5"], limit=1000)["obj_list"]}, {u["id"] for u in fetch(self.url, "SELECT id FROM users WHERE role IN (1, 5)")})
        self.assertEqual(users(filter=["role = 20"]), {"obj_list": [], "after": None})
        active = fetch(self.url, "SELECT id FROM users WHERE deactivated_at IS NULL")
        self.assertEqual({u["id"] for u in users(filter=["deactivated_at is null"], limit=1000)["obj_list"]}, {u["id"] for u in active})
        self.assertEqual({u["id"] for u in users(filter=["username ilike %alic%"])["obj_list"]}, {u["id"] for u in fetch(self.url, "SELECT id FROM users WHERE username ILIKE '%alic%'")})
        all_users = users(limit=1000)["obj_list"]
        self.assertEqual([u["id"] for u in all_users], [u["id"] for u in fetch(self.url, "SELECT id FROM users ORDER BY id DESC")])
        # one user a page, after the cursor: every user once, in the order of one big page
        seen, after = [], None
        while True:
            result = users(limit=1, **({"after": after} if after else {}))
            seen += result["obj_list"]
            if (after := result["after"]) is None: break
        self.assertEqual(seen, all_users)
        # other users columns are hidden from the filter and the order too, so their values can't be guessed
        for params in ({"filter": ["password is not null"]}, {"filter": ["email is null"]}, {"filter": [{"_or": [{"email": "is,null"}, {"id": ">,0"}]}]}, {"order": "email desc"}):
            with self.subTest(params=params):
                self.message(self.client.get("/private/user-read", params={key: json.dumps(value) if key == "filter" else value for key, value in params.items()}, headers=self.auth(self.alice)), 400)
        for params in ({"role": "5"}, {"table": "test"}, {"column": "password"}, {"relation": "[]"}):
            with self.subTest(params=params):
                self.message(self.client.get("/private/user-read", params=params, headers=self.auth(self.alice)), 400)
        self.message(self.client.get("/private/user-read"), 401)

    def test_object_read_group_column_gives_the_first_page_of_each_value(self):
        # a board: the first page of each value of a column in one call, every asked value present; a value's next page is a plain read with its after
        self.message(self.client.post("/public/object-create", params={"table": "test"}, json={"obj_list": [{"title": "board", "type": 7}] * 3 + [{"title": "board", "type": 8}]}))
        def read(**params):
            return self.message(self.client.get("/private/object-read", params={key: json.dumps(value) if key in ("filter", "group_values") else value for key, value in params.items()}, headers=self.auth(self.alice)))
        result = read(table="test", group_column="type", group_values=[7, 8, 9], filter=["title = board"], limit=2, column="id,type")
        expected = {value: [r["id"] for r in fetch(self.url, "SELECT id FROM test WHERE title = 'board' AND type = $1 ORDER BY id DESC", value)] for value in (7, 8, 9)}
        self.assertEqual(set(result["groups"]), {"7", "8", "9"})
        self.assertEqual([r["id"] for r in result["groups"]["7"]["obj_list"]], expected[7][:2])
        self.assertEqual({k for r in result["groups"]["7"]["obj_list"] for k in r}, {"id", "type"})
        self.assertEqual([r["id"] for r in result["groups"]["8"]["obj_list"]], expected[8])
        self.assertEqual(result["groups"]["9"], {"obj_list": [], "after": None})
        self.assertIsNone(result["groups"]["8"]["after"])
        rest = read(table="test", filter=["title = board", "type = 7"], after=result["groups"]["7"]["after"], limit=2)
        self.assertEqual([r["id"] for r in rest["obj_list"]], expected[7][2:])
        for params, status in (({"group_column": "type"}, 400), ({"group_column": "password", "group_values": [1]}, 400), ({"group_column": "type", "group_values": [7], "page": 2}, 400), ({"group_column": "nope", "group_values": [1]}, 400), ({"group_column": "type", "group_values": list(range(51))}, 400)):
            with self.subTest(params=params):
                self.message(self.client.get("/private/object-read", params={"table": "test", **{key: json.dumps(value) if key == "group_values" else value for key, value in params.items()}}, headers=self.auth(self.alice)), status)

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
        self.assertEqual(export.text.lstrip("\ufeff").split(), ["username", "alice", "bob"])
        self.message(self.client.post("/public/object-create", params={"table": "test"}, json={"title": "runner target"}))
        self.assertEqual(self.message(self.client.post("/admin/postgres-query-runner-write", json={"sql": "UPDATE test SET title = 'runner wrote' WHERE title = 'runner target'"}, headers=self.auth(self.admin))), "UPDATE 1")

    def test_admin_cannot_forge_audit_columns_run_ddl_or_change_itself(self):
        created = self.message(self.client.post("/admin/object-create", params={"table": "test"}, json={"title": "audit target"}, headers=self.auth(self.admin)))
        row_id = created[0] if isinstance(created, list) else fetch(self.url, "SELECT id FROM test WHERE title = 'audit target'")[0]["id"]
        for column, value in (("created_by_id", self.bob_id), ("created_at", "2020-01-01"), ("deleted_by_id", 1)):
            with self.subTest(column=column):
                self.assertIn(f"{column} is set by Atom", self.message(self.client.put("/admin/object-update", params={"table": "test"}, json={"id": row_id, column: value}, headers=self.auth(self.admin)), 400))
                self.assertIn(f"{column} is set by Atom", self.message(self.client.post("/admin/object-create", params={"table": "test"}, json={"title": "x", column: value}, headers=self.auth(self.admin)), 400))
        upload = lambda mode, csv: self.client.post("/admin/postgres-import", data={"mode": mode, "table": "test"}, files={"file": ("rows.csv", csv.encode(), "text/csv")}, headers=self.auth(self.admin))
        self.assertIn("created_by_id is set by Atom", self.message(upload("create", f"title,created_by_id\nforged,{self.bob_id}\n"), 400))
        self.assertEqual(fetch(self.url, "SELECT count(*) AS n FROM test WHERE title = 'forged'"), [{"n": 0}])
        self.message(upload("create", "title\nimported by admin\n"))
        self.assertEqual(fetch(self.url, "SELECT created_by_id FROM test WHERE title = 'imported by admin'"), [{"created_by_id": 1}])    # the importing admin, set by Atom
        write = lambda sql: self.client.post("/admin/postgres-query-runner-write", json={"sql": sql}, headers=self.auth(self.admin))
        for sql, message in (("DROP TABLE test", "DROP is not allowed"), ("TRUNCATE test", "TRUNCATE is not allowed"), ("DELETE FROM test", "DELETE needs a WHERE"), ("UPDATE test SET title = 'a' WHERE id = 1; DROP TABLE test", "one statement only")):
            with self.subTest(sql=sql): self.assertIn(message, self.message(write(sql), 400))
        self.assertIn("you cannot change your own permissions", self.message(self.client.put("/admin/user-update", json={"id": 1, "permissions": None}, headers=self.auth(self.admin)), 403))
        for column, value in (("role", 9), ("deactivated_at", "2026-01-01T00:00:00+00:00")):    # root's role and deactivation are refused by the root rule first
            with self.subTest(own=column): self.assertIn(f"root user {column} cannot be updated", self.message(self.client.put("/admin/user-update", json={"id": 1, column: value}, headers=self.auth(self.admin)), 400))

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
        email_token = self.message(self.client.post("/auth/login-email-otp", json={"role": 5, "email": "otp-user@example.test", "otp": 333333}))["access_token"]
        self.assertEqual(self.message(self.client.get("/my/profile", headers=self.auth(email_token)))["email"], "otp-user@example.test")
        fetch(self.url, "INSERT INTO otp (otp, mobile) VALUES (444444, '+910000000099')")
        mobile_token = self.message(self.client.post("/auth/login-mobile-otp", json={"role": 5, "mobile": "+910000000099", "otp": 444444}))["access_token"]
        self.assertEqual(self.message(self.client.get("/my/profile", headers=self.auth(mobile_token)))["mobile"], "+910000000099")
        self.assertEqual(fetch(self.url, "SELECT count(*) AS n FROM otp WHERE otp IN (111111, 333333, 444444)"), [{"n": 0}])    # used codes are deleted

    def test_token_refresh_needs_the_refresh_token(self):
        tokens = self.message(self.client.post("/auth/login-username-password", json={"username": "bob", "password": "bob-pass"}))
        self.assertEqual(self.message(self.client.post("/my/token-refresh", headers=self.auth(tokens["access_token"])), 401), "refresh token required")
        refreshed = self.message(self.client.post("/my/token-refresh", headers=self.auth(tokens["refresh_token"])))
        self.assertEqual(self.message(self.client.get("/my/profile", headers=self.auth(refreshed["access_token"])))["id"], self.bob_id)

    def test_token_refresh_refuses_a_deleted_or_deactivated_account(self):
        tokens = self.message(self.client.post("/auth/login-username-password", json={"username": "bob", "password": "bob-pass"}))
        for column, expected in (("deactivated_at", "account deactivated"), ("deleted_at", "account deleted")):
            with self.subTest(column=column):
                fetch(self.url, "UPDATE users SET deactivated_at = CASE WHEN $2 = 'deactivated_at' THEN now() END, deleted_at = CASE WHEN $2 = 'deleted_at' THEN now() END WHERE id = $1", self.bob_id, column)
                try: self.assertEqual(self.message(self.client.post("/my/token-refresh", headers=self.auth(tokens["refresh_token"])), 403), expected)
                finally: fetch(self.url, "UPDATE users SET deactivated_at = NULL, deleted_at = NULL WHERE id = $1", self.bob_id)

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
        self.assertEqual(unclosed_files(lambda: self.assertEqual(upload("missing_table").status_code, 403)), [])
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
        self.assertFalse([name for name, value in config.items() if "postgresql://" in str(value)])
        self.assertNotRegex(app.text, r"postgresql://[^:@/\"]+:(?!\*\*\*@)[^@\"]*@")    # the master DB line's URL comes masked, never with its password
        self.assertEqual(self.client.get("/admin/monitor", params={"view": "secrets"}, headers=self.auth(self.admin)).status_code, 400)
        self.assertEqual(self.client.get("/admin/monitor", params={"view": "requests", "hours": 5}, headers=self.auth(self.admin)).status_code, 400)

    def runtime_status(self):
        """This worker's background error counters and buffered rows, from the monitor's background view."""
        background = self.message(self.client.get("/admin/monitor", params={"view": "background"}, headers=self.auth(self.admin)))
        rows = lambda name: sum(item["rows"] for item in background["buffers"] if item["buffer"] == name)
        return {"error_count": {item["name"]: item["count"] for item in background["errors"]}, "buffer_rows_pending": {"create": rows("create"), "log_api": rows("log_api")}}

    def test_log_database_outage_is_counted_buffered_and_recovered(self):
        before = self.runtime_status()["error_count"]
        requests_sent = self.client.app.state.cache_postgres_table_rule["master"]["log_api"]["buffer_limit"] + 5    # enough to fill the buffer, so a request writes too
        info_logged = lambda: fetch(self.url, "SELECT count(*) AS n FROM log_api WHERE path = '/info'")[0]["n"]
        time.sleep(1.2)    # let earlier requests flush so the baseline is complete
        logged_before = info_logged()
        fetch(self.url, "ALTER TABLE log_api RENAME TO log_api_offline")
        try:
            with redirect_stdout(io.StringIO()):
                self.assertEqual({self.client.get("/info").status_code for _ in range(requests_sent)}, {200})    # the API keeps answering
                time.sleep(1.5)    # at least one periodic flush attempt (config_postgres_buffer_flush_auto_sec=1)
                during = self.runtime_status()
        finally:
            fetch(self.url, "ALTER TABLE log_api_offline RENAME TO log_api")
        self.assertGreater(during["error_count"]["log_api_write"], before["log_api_write"])
        self.assertGreater(during["error_count"]["buffer_flush"], before["buffer_flush"])
        self.assertGreater(during["buffer_rows_pending"]["log_api"], 0)    # rows wait in memory instead of being lost
        deadline, logged = time.time() + 5, 0
        while time.time() < deadline and logged < logged_before + requests_sent:
            logged = info_logged()
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
        self.assertIn("my create not allowed for table: no_such_table", log.getvalue())
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
        ready = self.message(self.client.get("/health-ready"))
        self.assertTrue(ready["postgres.master"]["is_ok"], ready)
        self.assertEqual(self.message(self.client.post("/my/ping", headers=self.auth(self.alice))), "pong")
        self.assertEqual(fetch(self.url, "SELECT last_active_at IS NOT NULL AS is_set FROM users WHERE id = $1", self.alice_id), [{"is_set": True}])
        encoded = self.message(self.client.get("/public/converter-number", params={"datatype": "int", "mode": "encode", "x": "12345"}))
        self.assertEqual(str(self.message(self.client.get("/public/converter-number", params={"datatype": "int", "mode": "decode", "x": str(encoded)}))), "12345")


if __name__ == "__main__":
    unittest.main()
