"""A second database gets its own schema at startup (config_postgres_schema_<name>): a table without id, keyed by (device, time), created there and not on master; reads take an order, update says it needs id; tables outside the schema get no Atom triggers and no root user."""
import json
import unittest
from tests.integration.support import app_login
from tests.integration.support import app_start
from tests.integration.support import app_stop
from tests.integration.support import create_database
from tests.integration.support import drop_database
from tests.integration.support import fetch
from tests.integration.support import requires_postgres

TELEMETRY = {"table": {"reading": {"column": [{"name": "device", "datatype": "text", "is_primary": True}, {"name": "time", "datatype": "timestamptz", "is_primary": True},
                                   {"name": "value", "datatype": "float8"}, {"name": "note", "datatype": "text", "index": "btree(note)"}, {"name": "updated_by_id", "datatype": "bigint"}]}},
             "sql": {"reading_seed": "INSERT INTO reading (device, time, value) VALUES ('a1', '2026-01-01T00:00:00Z', 1.5) ON CONFLICT DO NOTHING"}}


@requires_postgres
class SchemaDatabaseIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name, cls.url = create_database()
        cls.other_name, cls.other_url = create_database()
        fetch(cls.other_url, "CREATE TABLE vendor (id bigserial PRIMARY KEY, updated_at timestamptz)")    # tables the project manages itself, outside the schema
        fetch(cls.other_url, "CREATE TABLE users (id bigserial PRIMARY KEY, username text, password text, role smallint, deleted_at timestamptz, deactivated_at timestamptz, UNIQUE (username, role))")
        cls.handle = app_start(env={"config_postgres_url_master": cls.url, "config_postgres_url_telemetry": cls.other_url, "config_postgres_schema_telemetry": json.dumps(TELEMETRY)})
        cls.app, cls.client = cls.handle["app"], cls.handle["client"]
        cls.admin = {"Authorization": f"Bearer {app_login(cls.client, path='/auth/login-username-password', body={'username': 'admin', 'password': 'root-test-password'})}"}

    @classmethod
    def tearDownClass(cls):
        try: app_stop(cls.handle)
        finally:
            drop_database(cls.db_name)
            drop_database(cls.other_name)

    def test_the_table_is_created_on_its_own_database_with_its_key(self):
        key = fetch(self.other_url, "SELECT array_agg(a.attname::text ORDER BY array_position(i.indkey, a.attnum)) AS cols FROM pg_index i JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) WHERE i.indrelid = 'reading'::regclass AND i.indisprimary")
        self.assertEqual(key[0]["cols"], ["device", "time"])
        self.assertEqual(fetch(self.other_url, "SELECT count(*) AS n FROM pg_indexes WHERE indexname = 'idx_reading_note_btree'")[0]["n"], 1)
        self.assertEqual(fetch(self.url, "SELECT to_regclass('reading') IS NULL AS missing")[0]["missing"], True, "not on master")
        self.assertEqual(fetch(self.other_url, "SELECT to_regclass('log_api') IS NULL AS missing")[0]["missing"], True, "Atom's tables stay on master")
        self.assertIn("reading", self.app.state.cache_postgres_schema_dict["telemetry"])

    def test_routes_on_a_table_without_id(self):
        read = lambda **params: self.client.get("/admin/object-read", params={"connection": "telemetry", "table": "reading", **params}, headers=self.admin)
        self.assertEqual((read().status_code, read().json()["message"]), (400, "table has no id: pass order (e.g. order=time desc)"))
        self.assertEqual([row["device"] for row in read(order="time desc,device").json()["message"]["obj_list"]], ["a1"])
        update = self.client.put("/admin/object-update", params={"connection": "telemetry", "table": "reading"}, json={"id": 1, "value": 2.0}, headers=self.admin)
        self.assertEqual((update.status_code, update.json()["message"]), (400, "table 'reading' has no id: update needs one"))

    def test_tables_outside_the_schema_are_left_alone(self):
        triggers = {row["tgname"] for row in fetch(self.other_url, "SELECT t.tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid WHERE NOT t.tgisinternal AND c.relname IN ('vendor', 'users')")}
        self.assertEqual(triggers, set(), "no truncate, updated_at or users triggers on tables the schema does not list")
        self.assertEqual(fetch(self.other_url, "SELECT count(*) AS n FROM users")[0]["n"], 0, "the root user only where the schema has users (master)")
        self.assertEqual(self.client.get("/admin/object-read", params={"connection": "telemetry", "table": "vendor"}, headers=self.admin).status_code, 403, "closed: not in the schema")


if __name__ == "__main__":
    unittest.main()
