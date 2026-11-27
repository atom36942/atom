"""Schemas per database: config_postgres_schema_<name> collected master first, checked at startup (names, tables, where log_api lives), tables without id or with a key over several columns, each table's own keys (who may do what, row_lock, buffer, retention, labels), and clear errors from routes that need id."""
import unittest
from types import SimpleNamespace
import config
from function import func_check_postgres_schema
from function import func_check_table_access
from function import func_buffer_limit
from function import func_column_regex
from function import func_postgres_column_regex_dict
from function import func_page_keys
from function import func_postgres_delete
from function import func_postgres_int_mapping
from function import func_postgres_log_database
from function import func_postgres_schema_config_validate
from function import func_postgres_schema_context_build
from function import func_postgres_schema_dict
from function import func_postgres_table_rule_dict
from function import func_postgres_update
from tests.support import database

MASTER = config.config_postgres_schema_master
READING = {"column": [{"name": "time", "datatype": "timestamptz", "is_primary": True}, {"name": "device", "datatype": "text", "is_primary": True}, {"name": "value", "datatype": "float8"}]}


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
                                ({"config_postgres_schema_telemetry": {"table": {"reading": {"column": [{"name": "id", "datatype": "text"}]}}}}, "config_postgres_schema_telemetry: reading.id must be an integer column"),
                                ({"config_postgres_schema_telemetry": {}}, "config_postgres_schema_telemetry: schema missing")):
            with self.subTest(message=message), self.assertRaisesRegex(Exception, message): self.check(**values)

    def test_log_api_lives_in_one_schema_whose_database_gets_the_logs(self):
        without = {**MASTER, "table": {k: v for k, v in MASTER["table"].items() if k != "log_api"}}
        telemetry = {"table": {"log_api": MASTER["table"]["log_api"]}}
        self.check(config_postgres_schema_master=without, config_postgres_schema_telemetry=telemetry)
        self.assertEqual(func_postgres_log_database(schemas={"master": without, "telemetry": telemetry}), "telemetry")
        self.assertEqual(func_postgres_log_database(schemas={"master": MASTER}), "master")
        with self.assertRaisesRegex(Exception, r"config_is_log_api is on but no config_postgres_schema_<name> has log_api"):
            self.check(config_postgres_schema_master=without)
        with self.assertRaisesRegex(Exception, r"log_api is in config_postgres_schema_master and config_postgres_schema_telemetry: keep it in one"):
            self.check(config_postgres_schema_telemetry=telemetry)
        self.check(config_is_log_api=False, config_postgres_schema_master=without)    # logging off: no rule


class TableKeyTests(unittest.TestCase):
    def test_id_is_optional_and_a_key_may_span_columns(self):
        for columns in (READING, [{"name": "title", "datatype": "text"}], [{"name": "title", "datatype": "text"}, {"name": "id", "datatype": "bigint", "identity": "always", "is_primary": True}]):
            with self.subTest(columns=columns): func_postgres_schema_config_validate(config_postgres_schema={"table": {"t": columns if isinstance(columns, dict) else {"column": columns}}})

    def test_primary_columns_and_identity_rules(self):
        for columns, message in (([{"name": "time", "datatype": "timestamptz", "is_primary": True, "index": "btree(time)"}], r"t.time is a primary column: it takes only name, datatype, identity and is_primary \(not index\)"),
                                 ([{"name": "n", "datatype": "bigint", "identity": "always"}], "identity .* only on an integer primary column"),
                                 ([{"name": "n", "datatype": "text", "identity": "always", "is_primary": True}], "identity .* only on an integer primary column")):
            with self.subTest(message=message), self.assertRaisesRegex(Exception, message): func_postgres_schema_config_validate(config_postgres_schema={"table": {"t": {"column": columns}}})


class TableRuleTests(unittest.TestCase):
    COLUMNS = [{"name": "id", "datatype": "bigint", "identity": "always", "is_primary": True}, {"name": "created_at", "datatype": "timestamptz"}, {"name": "status", "datatype": "smallint", "in": (1, 2), "int_mapping": {1: "Open", 2: "Done"}}, {"name": "note", "datatype": "text", "is_private_read_blocked": True}]

    def validate(self, **keys):
        func_postgres_schema_config_validate(config_postgres_schema={"table": {"task": {**keys, "column": self.COLUMNS}}})

    def test_table_keys_are_checked(self):
        self.validate(public=["read"], private=["read"], my=["create", "read", "update", "delete", "delete_all"], admin=["create", "read", "update", "delete"], row_lock=["update", "delete"], row_delete_max=100, users_delete_skip=True, buffer_limit=500, retention_day=90)
        self.validate()    # only column is required: closed to every object route
        for keys, message in (({"public": ["delete"]}, "task.public: delete is not an action of /public routes"), ({"private": ["create"]}, "task.private: create is not an action"),
                              ({"admin": ["delete_all"]}, "task.admin: delete_all is not an action"), ({"my": "read"}, "task.my must be a list of actions"), ({"my": ["read", "read"]}, "lists an action twice"),
                              ({"row_lock": ["read"]}, "row_lock must be a list of update and/or delete"), ({"buffer_limit": 5}, "buffer_limit must be an integer from 10 to 5000"),
                              ({"retention_day": 0}, "retention_day must be an integer from 1"), ({"row_delete_max": True}, "row_delete_max must be an integer"), ({"users_delete_skip": 1}, "users_delete_skip must be bool"),
                              ({"publc": ["read"]}, "task: unknown key publc")):
            with self.subTest(keys=keys), self.assertRaisesRegex(Exception, message): self.validate(**keys)
        with self.assertRaisesRegex(Exception, r"task must be a dict with a column list: \{\"column\": \[...\]\} \(Atom 23.0.0\)"):
            func_postgres_schema_config_validate(config_postgres_schema={"table": {"task": self.COLUMNS}})
        with self.assertRaisesRegex(Exception, "retention_day needs a created_at column"):
            func_postgres_schema_config_validate(config_postgres_schema={"table": {"task": {"retention_day": 7, "column": [{"name": "id", "datatype": "bigint"}]}}})
        with self.assertRaisesRegex(Exception, "users: admin create not allowed"):
            func_postgres_schema_config_validate(config_postgres_schema={"table": {"users": {"admin": ["create", "read"], "column": [{"name": "id", "datatype": "bigint"}]}}})
        with self.assertRaisesRegex(Exception, r"control.table_row_delete_disable removed in Atom 23.0.0: set row_lock"):
            func_postgres_schema_config_validate(config_postgres_schema={"control": {"table_row_delete_disable": ["users"]}, "table": {}})

    def test_column_labels_are_checked(self):
        for column, message in (({"name": "note", "datatype": "text", "int_mapping": {1: "A"}}, "int_mapping only on an integer column"), ({"name": "n", "datatype": "smallint", "int_mapping": {"1": "A"}}, "integer codes"),
                                ({"name": "n", "datatype": "smallint", "int_mapping": {}}, "integer codes"), ({"name": "n", "datatype": "smallint", "in": (1, 2), "int_mapping": {1: "A"}}, "must be the same"),
                                ({"name": "n", "datatype": "smallint", "is_private_read_blocked": "yes"}, "is_private_read_blocked must be bool")):
            with self.subTest(column=column), self.assertRaisesRegex(Exception, message): func_postgres_schema_config_validate(config_postgres_schema={"table": {"t": {"column": [column]}}})
        func_postgres_schema_config_validate(config_postgres_schema={"table": {"t": {"column": [{"name": "n", "datatype": "smallint", "in": (1, 2), "int_mapping": {None: "Pending", 1: "A", 2: "B"}}]}}})    # None labels "no value yet"
        func_postgres_schema_config_validate(config_postgres_schema={"table": {"t": {"column": [{"name": "tags", "datatype": "smallint[]", "int_mapping": {1: "A", 2: "B"}}]}}})    # an integer array: each item has a label

    def test_rules_labels_and_triggers_come_from_the_tables(self):
        schemas = {"master": {"table": {"task": {"my": ["read"], "buffer_limit": 500, "row_lock": ["delete"], "row_delete_max": 50, "column": self.COLUMNS}, "users": {"column": [{"name": "id", "datatype": "bigint"}]}}}, "logs": {"table": {"event": {"admin": ["read"], "column": self.COLUMNS}}}}
        rules = func_postgres_table_rule_dict(schemas=schemas)
        self.assertEqual(rules["master"]["task"], {"my": ["read"], "buffer_limit": 500, "row_lock": ["delete"], "row_delete_max": 50, "private_read_blocked": ["note"]})
        self.assertEqual(rules["logs"]["event"]["admin"], ["read"])
        labels = func_postgres_int_mapping(schemas=schemas, config_users_role_label={1: "Admin", 2: "User"}, config_api={"/admin/b": {"id": 70, "user_check_permission": {"mode": "token"}}, "/admin/a": {"id": 63, "user_check_permission": {"mode": "token"}}, "/my/x": {"id": 5}})
        self.assertEqual(labels, {"master": {"task": {"status": {1: "Open", 2: "Done"}}, "users": {"role": {1: "Admin", 2: "User"}, "permissions": {63: "/admin/a", 70: "/admin/b"}}}, "logs": {"event": {"status": {1: "Open", 2: "Done"}}}})
        context = func_postgres_schema_context_build(config_postgres_schema=schemas["master"])
        self.assertEqual((context["tables"], context["bulk_blocked"], context["table_blocked"], context["update_blocked"]), ({"task", "users"}, [["task", 50]], ["task"], []))

    def test_routes_allow_only_what_the_table_lists(self):
        state = SimpleNamespace(cache_postgres_table_rule=func_postgres_table_rule_dict(schemas={"master": {"table": {"task": {"my": ["read", "update"], "buffer_limit": 500, "column": self.COLUMNS}, "tag": {"my": ["create"], "column": self.COLUMNS}}}, "logs": {"table": {"event": {"admin": ["read"], "column": self.COLUMNS}}}}))
        func_check_table_access(app_state=state, table="task", group="my", action="read")
        func_check_table_access(app_state=state, connection="logs", table="event", group="admin", action="read")
        for kwargs, message in (({"table": "task", "group": "my", "action": "delete"}, r"my delete not allowed for table: task \(add \"delete\" to \"my\" of task in config_postgres_schema_master\)"),
                                ({"table": "task", "group": "public", "action": "read"}, "public read not allowed for table: task"), ({"table": "other", "group": "admin", "action": "read"}, "admin read not allowed for table: other"),
                                ({"table": "task", "group": "my", "action": "read", "relation": ["tags,tag,id,task_id"]}, "my read not allowed for table: tag"),
                                ({"connection": "logs", "table": "task", "group": "my", "action": "read"}, "config_postgres_schema_logs")):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(Exception, message) as raised: func_check_table_access(app_state=state, **kwargs)
            self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual((func_buffer_limit(app_state=state, table="task"), func_buffer_limit(app_state=state, table="tag"), func_buffer_limit(app_state=state, table="event", connection="logs")), (500, 100, 100))

    def test_format_rules_live_on_their_columns(self):
        schemas = {"master": {"table": {"customer": {"column": [{"name": "email", "datatype": "text", "regex": "^[^@]+@[^@]+$", "regex_message": "Email must look like name@example.com"}, {"name": "code", "datatype": "text", "regex": "^[A-Z]{2}$"}]},
                                        "contact": {"column": [{"name": "email", "datatype": "text"}]}}}, "logs": {"table": {"event": {"column": [{"name": "code", "datatype": "text", "regex": "^[0-9]+$"}]}}}}
        rules = func_postgres_column_regex_dict(schemas=schemas)
        self.assertEqual(rules, {"master": {"customer": {"email": ["^[^@]+@[^@]+$", "Email must look like name@example.com"], "code": ["^[A-Z]{2}$", "code: invalid format"]}}, "logs": {"event": {"code": ["^[0-9]+$", "code: invalid format"]}}})
        state = SimpleNamespace(cache_column_regex=rules)
        self.assertEqual(func_column_regex(app_state=state, table="contact"), {}, "the same column name in another table has its own rule, or none")
        self.assertEqual(func_column_regex(app_state=state, table="event", connection="logs"), {"code": ["^[0-9]+$", "code: invalid format"]})
        for column, message in (({"name": "n", "datatype": "text", "regex_message": "x"}, "the column needs regex"), ({"name": "n", "datatype": "text", "regex": "^(a$"}, "invalid regex"),
                                ({"name": "n", "datatype": "text", "regex": "^a'$"}, "single quote"), ({"name": "n", "datatype": "text", "regex": "^a$", "regex_message": ""}, "regex_message is the error")):
            with self.subTest(column=column), self.assertRaisesRegex(Exception, message): func_postgres_schema_config_validate(config_postgres_schema={"table": {"t": {"column": [column]}}})
        atom = func_postgres_column_regex_dict(schemas={"master": MASTER})["master"]["users"]
        self.assertEqual(sorted(atom), ["email_secondary", "mobile_secondary", "password", "username"])
        self.assertEqual(atom["password"][1], "Password must be 6-120 characters and contain no spaces")

    def test_atom_tables_keep_their_access(self):
        rules = func_postgres_table_rule_dict(schemas={"master": MASTER})["master"]
        for table in ("log_api", "log_users_password", "log_users_delete", "script_run", "queue_job", "otp", "users"):
            with self.subTest(table=table): self.assertEqual(rules[table]["admin"], ["read"], "only Atom writes these")
        for table in ("users", "config", "webhook", "log_users_password", "otp", "script_run", "queue_job"): self.assertNotIn("my", rules[table])
        self.assertEqual({table for table, rule in rules.items() if "delete_all" in rule.get("my", [])}, {"test", "message", "notification"})
        self.assertEqual({table for table, rule in rules.items() if rule.get("public")}, {"test"})
        self.assertEqual((rules["log_api"]["buffer_limit"], rules["log_api"]["retention_day"], rules["otp"]["retention_day"], rules["script_run"]["retention_day"]), (1000, 7, 1, 90))
        self.assertEqual(rules["script_run"]["private_read_blocked"], ["started_by", "host", "step", "message", "peak_memory_mb"])
        self.assertEqual({table for table, rule in rules.items() if rule.get("users_delete_skip")}, {"users", "log_users_delete"})


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
