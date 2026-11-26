"""Schemas per database: config_postgres_schema_<name> collected master first, checked at startup (names, tables, where log_api lives), tables without id or with a key over several columns, and clear errors from routes that need id."""
import unittest
from types import SimpleNamespace
import config
from function import func_check_postgres_schema
from function import func_page_keys
from function import func_postgres_delete
from function import func_postgres_schema_config_validate
from function import func_postgres_schema_dict
from function import func_postgres_update
from tests.support import database

MASTER = config.config_postgres_schema_master
READING = [{"name": "time", "datatype": "timestamptz", "is_primary": True}, {"name": "device", "datatype": "text", "is_primary": True}, {"name": "value", "datatype": "float8"}]


class SchemaDictTests(unittest.TestCase):
    def test_every_schema_by_name_master_first(self):
        values = {"config_postgres_schema_telemetry": {"table": {}}, "config_postgres_schema_master": MASTER, "config_postgres_lock_timeout_sec": 10, "config_other": 1}
        self.assertEqual(list(func_postgres_schema_dict(values=values)), ["master", "telemetry"])


class SchemaCheckTests(unittest.TestCase):
    def check(self, **values):
        func_check_postgres_schema(app_state=SimpleNamespace(**{"config_postgres_schema_master": MASTER, "config_postgres_url_dict": {"master": "postgresql://x", "telemetry": "postgresql://y"}, **values}))

    def test_a_database_schema_with_tables_without_id(self):
        self.check(config_postgres_schema_telemetry={"extension": ["timescaledb"], "table": {"reading": READING}, "sql": {"reading_hypertable": "SELECT create_hypertable('reading', 'time', if_not_exists => TRUE)"}})

    def test_wrong_schemas_stop_startup(self):
        for values, message in (({"config_postgres_schema_master": None}, "config_postgres_schema_master is required"),
                                ({"config_postgres_schema_telemtry": {"table": {}}}, r"config_postgres_schema_telemtry: no database named telemtry \(config_postgres_url_telemtry is not set\)"),
                                ({"config_postgres_schema_telemetry": {"table": {"reading": [{"name": "id", "datatype": "text"}]}}}, "config_postgres_schema_telemetry: reading.id must be an integer column"),
                                ({"config_postgres_schema_telemetry": {}}, "config_postgres_schema_telemetry: schema missing")):
            with self.subTest(message=message), self.assertRaisesRegex(Exception, message): self.check(**values)

    def test_log_api_lives_only_in_the_schema_of_its_database(self):
        without = {**MASTER, "table": {k: v for k, v in MASTER["table"].items() if k != "log_api"}}
        self.check(config_postgres_db_log_api="telemetry", config_postgres_schema_master=without, config_postgres_schema_telemetry={"table": {"log_api": MASTER["table"]["log_api"]}})
        with self.assertRaisesRegex(Exception, r"config_postgres_db_log_api is 'telemetry': add log_api to config_postgres_schema_telemetry"):
            self.check(config_postgres_db_log_api="telemetry", config_postgres_schema_telemetry={"table": {}})
        with self.assertRaisesRegex(Exception, r"log_api is in config_postgres_schema_master, but API logs go to 'telemetry'"):
            self.check(config_postgres_db_log_api="telemetry", config_postgres_schema_telemetry={"table": {"log_api": MASTER["table"]["log_api"]}})
        self.check(config_is_log_api=False, config_postgres_db_log_api="telemetry", config_postgres_schema_master=without)    # logging off: no rule


class TableKeyTests(unittest.TestCase):
    def test_id_is_optional_and_a_key_may_span_columns(self):
        for columns in (READING, [{"name": "title", "datatype": "text"}], [{"name": "title", "datatype": "text"}, {"name": "id", "datatype": "bigint", "identity": "always", "is_primary": True}]):
            with self.subTest(columns=columns): func_postgres_schema_config_validate(config_postgres_schema={"table": {"t": columns}})

    def test_primary_columns_and_identity_rules(self):
        for columns, message in (([{"name": "time", "datatype": "timestamptz", "is_primary": True, "index": "btree(time)"}], r"t.time is a primary column: it takes only name, datatype, identity and is_primary \(not index\)"),
                                 ([{"name": "n", "datatype": "bigint", "identity": "always"}], "identity .* only on an integer primary column"),
                                 ([{"name": "n", "datatype": "text", "identity": "always", "is_primary": True}], "identity .* only on an integer primary column")):
            with self.subTest(message=message), self.assertRaisesRegex(Exception, message): func_postgres_schema_config_validate(config_postgres_schema={"table": {"t": columns}})


class RoutesNeedingIdTests(unittest.IsolatedAsyncioTestCase):
    SCHEMA = {"reading": {"time": {"datatype": "timestamp with time zone"}, "device": {"datatype": "text"}, "value": {"datatype": "double precision"}}}

    def test_read_without_id_needs_an_order(self):
        with self.assertRaisesRegex(Exception, r"table has no id: pass order") as raised: func_page_keys(order="", columns=self.SCHEMA["reading"])
        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual([key["name"] for key in func_page_keys(order="time desc,device", columns=self.SCHEMA["reading"])], ["time", "device"], "no id added to the order")

    async def test_update_and_delete_need_id(self):
        pool, conn = database()
        with self.assertRaisesRegex(Exception, "table 'reading' has no id: update needs one") as raised:
            await func_postgres_update(client_postgres=pool, client_postgres_conn=None, client_password_hasher=None, cache_postgres_schema=self.SCHEMA, config_column_regex={}, table="reading", obj_list=[{"value": 1.0}], created_by_id=None)
        self.assertEqual(raised.exception.status_code, 400)
        with self.assertRaisesRegex(Exception, "table 'reading' has no id: delete needs one"):
            await func_postgres_delete(client_postgres=pool, client_postgres_conn=None, cache_postgres_schema=self.SCHEMA, table="reading", ids=[1], created_by_id=None)
        conn.fetch.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
