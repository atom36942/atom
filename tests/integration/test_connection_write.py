"""Writes to a second database: ?connection= on write routes, buffered rows flushed to their own database, ON CONFLICT DO NOTHING on a table without id, and the ip_allow and token_verify route checks."""
import time
import unittest
from fastapi.testclient import TestClient
from tests.integration.support import app_login
from tests.integration.support import app_start
from tests.integration.support import app_stop
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import fetch
from tests.integration.support import requires_postgres


@requires_postgres
class ConnectionWriteIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name, cls.url = create_database()
        cls.other_name, cls.other_url = create_database()
        fetch(cls.other_url, "CREATE TABLE note (id bigserial PRIMARY KEY, title text, created_by_id bigint, updated_by_id bigint, created_at timestamptz DEFAULT now(), updated_at timestamptz)")
        fetch(cls.other_url, "CREATE TABLE reading (time timestamptz NOT NULL, device text NOT NULL, value double precision, PRIMARY KEY (device, time))")    # like a hypertable: no id, the key includes time
        cls.handle = app_start(env={"config_postgres_url_master": cls.url, "config_postgres_url_telemetry": cls.other_url, "config_postgres_buffer_flush_auto_sec_telemetry": "1", "config_postgres_buffer_flush_auto_sec": "3600"})
        cls.app, cls.client = cls.handle["app"], cls.handle["client"]
        cls.app.state.cache_postgres_table_rule["telemetry"] = {"note": {"private_read_blocked": []}}    # as config_postgres_schema_telemetry would list note (its tables are made above)
        cls.admin = {"Authorization": f"Bearer {app_login(cls.client, path='/auth/login-username-password', body={'username': 'admin', 'password': 'root-test-password'})}"}
        cls.user = {"Authorization": f"Bearer {app_login(cls.client, path='/auth/signup-username-password', body={'role': 5, 'username': 'bob', 'password': 'bob-pass'})}"}

    @classmethod
    def tearDownClass(cls):
        try: app_stop(cls.handle)
        finally:
            drop_database(cls.db_name)
            drop_database(cls.other_name)

    def count(self, url, sql):
        return fetch(url, sql)[0]["n"]

    def test_admin_writes_go_to_the_named_database(self):
        response = self.client.post("/admin/object-create", params={"table": "note", "connection": "telemetry"}, json={"title": "direct"}, headers=self.admin)
        self.assertEqual(response.status_code, 200, response.text)
        note_id = response.json()["message"][0]
        self.assertEqual(self.count(self.other_url, "SELECT count(*) AS n FROM note WHERE title = 'direct'"), 1)
        self.assertEqual(self.client.put("/admin/object-update", params={"table": "note", "connection": "telemetry"}, json={"id": note_id, "title": "changed"}, headers=self.admin).status_code, 200)
        self.assertEqual(self.count(self.other_url, "SELECT count(*) AS n FROM note WHERE title = 'changed'"), 1)
        self.assertEqual(self.client.post("/admin/object-create", params={"table": "note"}, json={"title": "x"}, headers=self.admin).json()["message"], "admin create not allowed for table: note (not in config_postgres_schema_master)", "without connection: master, whose schema has no note table")

    def test_buffered_rows_are_flushed_to_their_own_database_on_its_interval(self):
        response = self.client.post("/admin/object-create", params={"table": "note", "connection": "telemetry", "mode": "buffer"}, json={"title": "buffered"}, headers=self.admin)
        self.assertEqual(response.json()["message"], "buffered", response.text)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not self.count(self.other_url, "SELECT count(*) AS n FROM note WHERE title = 'buffered'"): time.sleep(0.2)
        self.assertEqual(self.count(self.other_url, "SELECT count(*) AS n FROM note WHERE title = 'buffered'"), 1, "telemetry flushes every second, master's hour does not hold it back")

    def test_on_conflict_nothing_and_no_returning_on_a_table_without_id(self):
        state = self.app.state
        rows = [{"time": "2026-01-01T00:00:00+00:00", "device": "a1", "value": 1.5}]
        async def write(mode):
            return await state.func_postgres_create(client_postgres=state.client_postgres_dict["telemetry"], client_postgres_conn=None, client_password_hasher=None, cache_postgres_schema=state.cache_postgres_schema_dict["telemetry"], buffer_postgres=state.buffer_postgres_create, config_column_regex={}, buffer_limit=100, mode=mode, table="reading", obj_list=rows, connection="telemetry", on_conflict="nothing")
        async def run():
            self.assertEqual(await write("now"), "created")
            self.assertEqual(await write("now"), "created", "the same point again is skipped, not an error")
            for _ in range(3): await write("buffer")
            await state.func_postgres_buffer_flush_all(app_state=state)
        self.client.portal.call(run)    # on the app's own event loop, where its pools live
        self.assertEqual(self.count(self.other_url, "SELECT count(*) AS n FROM reading"), 1)
        self.assertEqual(state.buffer_postgres_create, {})

    def test_routes_without_the_flag_refuse_connection(self):
        response = self.client.post("/my/object-create", params={"table": "note", "connection": "telemetry"}, json={"title": "x"}, headers=self.user)
        self.assertEqual((response.status_code, response.json()["message"]), (400, "connection not allowed on this route"))

    def test_ip_allow_and_token_verify_on_a_route(self):
        state, path = self.app.state, "/public/object-create"
        saved = dict(state.config_api[path])
        try:
            state.config_api[path] = {**saved, "ip_allow": ["5.6.7.0/24"]}
            outside, inside = TestClient(self.app, client=("9.9.9.9", 50000)), TestClient(self.app, client=("5.6.7.8", 50000))
            self.assertEqual(outside.post(path, params={"table": "test"}, json={"title": "x"}).status_code, 403)
            self.assertNotEqual(inside.post(path, params={"table": "test"}, json={"title": "x"}).status_code, 403)
            state.config_api[path] = {**saved, "token_verify": {"secret": "config_webhook_token_test"}}
            state.config_webhook_token_test = "s3cret-token"
            self.assertEqual(inside.post(path, params={"table": "test"}, json={"title": "x"}).status_code, 403)
            self.assertEqual(inside.post(path, params={"table": "test"}, json={"title": "x"}, headers={"x-webhook-token": "wrong"}).status_code, 403)
            self.assertNotEqual(inside.post(path, params={"table": "test"}, json={"title": "x"}, headers={"x-webhook-token": "s3cret-token"}).status_code, 403)
        finally:
            state.config_api[path] = saved


if __name__ == "__main__":
    unittest.main()
