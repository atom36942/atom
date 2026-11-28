"""Schemas per database: config_postgres_schema_<name> collected master first, checked at startup (names, tables, where log_api lives), tables without id or with a key over several columns, each table's own keys (who may do what, row_lock, buffer, retention, labels), and clear errors from routes that need id."""
import asyncio
import unittest
from types import SimpleNamespace
import config
from function import func_check_postgres_schema
from function import func_check_table_access
from function import func_buffer_limit
from function import func_postgres_control_table_check
from function import func_postgres_schema_users_init
from function import func_object_access
from function import func_postgres_ownership_column_dict
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
from function import func_postgres_users_access
from function import func_postgres_update
from tests.support import database

MASTER = config.config_postgres_schema_master
READING = {"column": [{"name": "time", "datatype": "timestamptz", "is_primary_key": True}, {"name": "device", "datatype": "text", "is_primary_key": True}, {"name": "value", "datatype": "float8"}]}


class SchemaDictTests(unittest.TestCase):
    def test_every_schema_by_name_master_first(self):
        values = {"config_postgres_schema_telemetry": {"table": {}}, "config_postgres_schema_master": MASTER, "config_postgres_lock_timeout_sec": 10, "config_other": 1}
        self.assertEqual(list(func_postgres_schema_dict(values=values)), ["master", "telemetry"])


class SchemaCheckTests(unittest.TestCase):
    def check(self, **values):
        func_check_postgres_schema(app_state=SimpleNamespace(**{"config_postgres_schema_master": MASTER, "config_postgres_url_dict": {"master": "postgresql://x", "telemetry": "postgresql://y"}, **values}))

    def test_a_database_schema_with_tables_without_id(self):
        self.check(config_postgres_schema_telemetry={"table": {"reading": READING}, "sql": {"reading_hypertable": "SELECT create_hypertable('reading', 'time', if_not_exists => TRUE)"}, "control": {"extension": ["timescaledb"]}})

    def test_wrong_schemas_stop_startup(self):
        for values, message in (({"config_postgres_schema_master": None}, "config_postgres_schema_master is required"),
                                ({"config_postgres_schema_telemtry": {"table": {}}}, r"config_postgres_schema_telemtry: no database named telemtry \(config_postgres_url_telemtry is not set\)"),
                                ({"config_postgres_schema_telemetry": {"table": {"reading": {"column": [{"name": "id", "datatype": "text"}]}}}}, "config_postgres_schema_telemetry: reading.id must be an integer column"),
                                ({"config_postgres_schema_telemetry": []}, "config_postgres_schema_telemetry: schema missing")):
            with self.subTest(message=message), self.assertRaisesRegex(Exception, message): self.check(**values)

    def test_log_api_lives_in_one_schema_whose_database_gets_the_logs(self):
        control = {key: ([t for t in value if t != "log_api"] if isinstance(value, list) and key != "extension" else {t: n for t, n in value.items() if t != "log_api"} if isinstance(value, dict) else value) for key, value in MASTER["control"].items()}    # log_api's control entries move with it
        without = {**MASTER, "table": {k: v for k, v in MASTER["table"].items() if k != "log_api"}, "control": control}
        telemetry = {"table": {"log_api": MASTER["table"]["log_api"]}, "control": {"row_update_disabled": ["log_api"], "buffer_limit": {"log_api": 1000}, "retention_day": {"log_api": 7}}}
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
        for columns in (READING, [{"name": "title", "datatype": "text"}], [{"name": "title", "datatype": "text"}, {"name": "id", "datatype": "bigint", "identity": "always", "is_primary_key": True}]):
            with self.subTest(columns=columns): func_postgres_schema_config_validate(config_postgres_schema={"table": {"t": columns if isinstance(columns, dict) else {"column": columns}}})

    def test_primary_columns_and_identity_rules(self):
        for columns, message in (([{"name": "time", "datatype": "timestamptz", "is_primary_key": True, "index": ["btree(time)"]}], r"t.time is a primary key column: it takes only name, datatype, identity and is_primary_key \(not index\)"),
                                 ([{"name": "n", "datatype": "bigint", "identity": "always"}], "identity .* only on an integer primary key column"),
                                 ([{"name": "n", "datatype": "text", "identity": "always", "is_primary_key": True}], "identity .* only on an integer primary key column")):
            with self.subTest(message=message), self.assertRaisesRegex(Exception, message): func_postgres_schema_config_validate(config_postgres_schema={"table": {"t": {"column": columns}}})

    def test_old_column_and_table_keys_stop_startup_with_the_new_name(self):
        for column, message in (({"name": "n", "datatype": "bigint", "is_primary": True}, "is_primary removed in Atom 24.0.0: use is_primary_key"), ({"name": "n", "datatype": "text", "is_mandatory": True}, "use is_not_null"),
                                ({"name": "n", "datatype": "text", "old": "m"}, "use old_name"), ({"name": "n", "datatype": "smallint", "in": (1, 2)}, "use allowed_values"),
                                ({"name": "n", "datatype": "text", "is_private_read_blocked": True}, r"use read_blocked: \["), ({"name": "n", "datatype": "text", "is_read_only": True}, r"use write_blocked: \["),
                                ({"name": "n", "datatype": "text", "users_access": ["token"]}, "users_access removed"), ({"name": "n", "datatype": "text", "colour": "red"}, "unknown key colour"),
                                ({"name": "n", "datatype": "text", "unique": "n"}, "unique must be a list of column lists"), ({"name": "n", "datatype": "text", "index": "btree(n)"}, "index must be a list of index texts"),
                                ({"name": "n", "datatype": "text", "index": ["btree(n)|gin(n)"]}, "no \\|")):
            with self.subTest(column=column), self.assertRaisesRegex(Exception, message): func_postgres_schema_config_validate(config_postgres_schema={"table": {"t": {"column": [column]}}})
        for keys, message in (({"public": ["read"]}, "t.public moved in Atom 24.0.0 to the schema's control: public_create / public_read"), ({"row_lock": ["delete"]}, "row_update_disabled / row_delete_disabled"),
                              ({"retention_day": 7}, "retention_day: \\{table: days\\}"), ({"admin": ["read"]}, "t.admin removed in Atom 24.0.0"), ({"publc": ["read"]}, "t: unknown key publc; a table has only column")):
            with self.subTest(keys=keys), self.assertRaisesRegex(Exception, message): func_postgres_schema_config_validate(config_postgres_schema={"table": {"t": {**keys, "column": [{"name": "n", "datatype": "text"}]}}})
        with self.assertRaisesRegex(Exception, r"t must be a dict with a column list"):
            func_postgres_schema_config_validate(config_postgres_schema={"table": {"t": [{"name": "n", "datatype": "text"}]}})


class TableRuleTests(unittest.TestCase):
    COLUMNS = [{"name": "id", "datatype": "bigint", "identity": "always", "is_primary_key": True}, {"name": "created_at", "datatype": "timestamptz"}, {"name": "created_by_id", "datatype": "bigint"}, {"name": "status", "datatype": "smallint", "allowed_values": [1, 2], "int_mapping": {1: "Open", 2: "Done"}, "write_blocked": ["my", "public"]},
               {"name": "note", "datatype": "text", "read_blocked": ["private"]}, {"name": "assigned_to_id", "datatype": "bigint", "ownership": ["read", "update"]}]

    def validate(self, **control):
        func_postgres_schema_config_validate(config_postgres_schema={"table": {"task": {"column": self.COLUMNS}, "users": {"column": [{"name": "id", "datatype": "bigint"}]}, "config": {"column": [{"name": "created_at", "datatype": "timestamptz"}]}, "event": {"column": [{"name": "created_at", "datatype": "timestamptz"}, {"name": "is_protected", "datatype": "boolean"}]}}, "control": control})

    def test_control_keys_are_checked(self):
        self.validate(public_read=["task"], private_read=["task"], my_create=["task"], my_read=["task", "users"], my_update=["task"], my_delete=["task"], my_delete_all=["task"], row_update_disabled=["event"], row_delete_disabled=["event"], row_delete_max={"task": 100}, buffer_limit={"task": 500}, is_truncate_disabled=False)
        self.validate()    # nothing listed: every table closed to /public, /private and /my
        for control, message in (({"row_update_disabled": ["tsk"]}, "control.row_update_disabled: tsk is not in this schema's table part"), ({"my_read": "task"}, "control.my_read must be a list of table names"), ({"my_read": ["task", "task"]}, "each once"),
                                 ({"public_delete": ["task"]}, "control: unknown key public_delete"), ({"private_create": ["task"]}, "unknown key private_create"), ({"buffer_limit": {"task": 5}}, "control.buffer_limit.task must be an integer from 10 to 5000"),
                                 ({"retention_day": {"task": 0}}, "control.retention_day.task must be an integer from 1"), ({"row_delete_max": {"task": True}}, "row_delete_max.task must be an integer"), ({"buffer_limit": ["task"]}, "buffer_limit must be \\{table: number\\}"),
                                 ({"my_create": ["users"]}, "control.my_create: users not allowed"), ({"row_update_disabled": ["users"]}, "row_update_disabled: users not allowed; Atom updates its rows"),
                                 ({"retention_day": {"users": 7}}, "retention_day: users not allowed"), ({"retention_day": {"config": 7}}, "retention_day: config not allowed"),
                                 ({"my_update": ["task"], "row_update_disabled": ["task"]}, "my_update: task is in row_update_disabled"), ({"admin_update": ["task"], "row_update_disabled": ["task"]}, "admin_update: task is in row_update_disabled"),
                                 ({"my_delete": ["task"], "row_delete_disabled": ["task"]}, "my_delete: task is in row_delete_disabled"), ({"my_delete_all": ["task"], "row_delete_disabled": ["task"]}, "my_delete_all: task"), ({"admin_delete": ["task"], "row_delete_disabled": ["task"]}, "admin_delete: task"),
                                 ({"my_create": ["event"]}, "my_create: event has no created_by_id, so"), ({"my_read": ["event"]}, "my_read: event has no created_by_id or column with ownership \\[\"read\"\\]"), ({"my_delete_all": ["event"]}, "ownership \\[\"delete\"\\]"),
                                 ({"retention_day": {"event": 7}}, "event has is_protected"), ({"retention_day": {"task": 7}, "row_delete_disabled": ["task"]}, "task is in row_delete_disabled"), ({"retention_day": {"task": 7}, "row_delete_max": {"task": 9}}, "task is in row_delete_max"),
                                 ({"is_truncate_table": False}, "control.is_truncate_table removed in Atom 24.0.0: use is_truncate_disabled"), ({"is_root_user_create": True}, "use config_is_root_user"), ({"is_log_users_delete": True}, "config_is_users_delete_log"), ({"is_totp_clear": True}, "config_is_totp_clear"),
                                 ({"is_updated_at_set": "yes"}, "control.is_updated_at_set must be True or False"), ({"table_row_delete_disable": ["users"]}, "control.table_row_delete_disable removed")):
            with self.subTest(control=control), self.assertRaisesRegex(Exception, message): self.validate(**control)
        with self.assertRaisesRegex(Exception, "retention_day: task needs a created_at column"):
            func_postgres_schema_config_validate(config_postgres_schema={"table": {"task": {"column": [{"name": "id", "datatype": "bigint"}]}}, "control": {"retention_day": {"task": 7}}})
        with self.assertRaisesRegex(Exception, "schema: unknown part extra"):
            func_postgres_schema_config_validate(config_postgres_schema={"table": {}, "extra": {}})

    def test_column_rules_are_checked(self):
        for column, message in (({"name": "note", "datatype": "text", "int_mapping": {1: "A"}}, "int_mapping only on an integer column"), ({"name": "n", "datatype": "smallint", "int_mapping": {"1": "A"}}, "integer codes"),
                                ({"name": "n", "datatype": "smallint", "int_mapping": {}}, "integer codes"), ({"name": "n", "datatype": "smallint", "allowed_values": [1, 2], "int_mapping": {1: "A"}}, "must be the same"),
                                ({"name": "n", "datatype": "smallint", "allowed_values": [1, "a"]}, "allowed_values must be a list of integers or of texts"), ({"name": "n", "datatype": "smallint", "allowed_values": []}, "allowed_values must be"),
                                ({"name": "n", "datatype": "text", "read_blocked": ["everyone"]}, "read_blocked must be a list of my, public, private, admin"), ({"name": "n", "datatype": "text", "write_blocked": []}, "write_blocked must be a list"),
                                ({"name": "n", "datatype": "text", "write_blocked": ["my", "my"]}, "each once"), ({"name": "n", "datatype": "bigint", "ownership": ["create"]}, "ownership must be a list of read, update, delete"),
                                ({"name": "created_by_id", "datatype": "bigint", "ownership": ["read"]}, "created_by_id is always the owner"), ({"name": "n", "datatype": "text", "is_not_null": "yes"}, "is_not_null must be True or False")):
            with self.subTest(column=column), self.assertRaisesRegex(Exception, message): func_postgres_schema_config_validate(config_postgres_schema={"table": {"t": {"column": [column]}}})
        func_postgres_schema_config_validate(config_postgres_schema={"table": {"t": {"column": [{"name": "n", "datatype": "smallint", "allowed_values": [1, 2], "int_mapping": {None: "Pending", 1: "A", 2: "B"}}]}}})    # None labels "no value yet"
        func_postgres_schema_config_validate(config_postgres_schema={"table": {"t": {"column": [{"name": "tags", "datatype": "smallint[]", "int_mapping": {1: "A", 2: "B"}}, {"name": "kind", "datatype": "text", "allowed_values": ["a", "b"]}]}}})

    def test_rules_labels_and_triggers_come_from_control_and_columns(self):
        control = {"my_read": ["task"], "my_update": ["task"], "buffer_limit": {"task": 500}, "row_delete_disabled": ["task"], "row_delete_max": {"task": 50}, "row_update_disabled": ["task"]}
        schemas = {"master": {"table": {"task": {"column": self.COLUMNS}, "users": {"column": [{"name": "id", "datatype": "bigint"}]}}, "control": control}, "logs": {"table": {"event": {"column": self.COLUMNS}}}}
        rules = func_postgres_table_rule_dict(schemas=schemas)
        task = rules["master"]["task"]
        self.assertEqual((task["my"], task["public"], task["private"], task["buffer_limit"], task["row_delete_max"], task["row_update_disabled"], task["row_delete_disabled"]), (["read", "update"], [], [], 500, 50, True, True))
        self.assertEqual((task["read_blocked"]["private"], task["read_blocked"]["admin"], task["write_blocked"]["my"], task["write_blocked"]["admin"]), (["note"], [], ["status"], []))
        self.assertEqual(task["ownership"], {"read": ["created_by_id", "assigned_to_id"], "update": ["created_by_id", "assigned_to_id"], "delete": ["created_by_id"]})
        self.assertEqual((rules["logs"]["event"]["my"], rules["master"]["users"]["ownership"]["read"]), ([], []))
        self.assertEqual(func_postgres_ownership_column_dict(rules=rules), {"read": ["created_by_id", "assigned_to_id"], "update": ["created_by_id", "assigned_to_id"], "delete": ["created_by_id"]})
        labels = func_postgres_int_mapping(schemas=schemas, config_users_role_label={1: "Admin", 2: "User"}, config_api={"/admin/b": {"id": 70, "user_check_permission": {"mode": "token"}}, "/admin/a": {"id": 63, "user_check_permission": {"mode": "token"}}, "/my/x": {"id": 5}})
        self.assertEqual(labels, {"master": {"task": {"status": {1: "Open", 2: "Done"}}, "users": {"role": {1: "Admin", 2: "User"}, "permissions": {63: "/admin/a", 70: "/admin/b"}}}, "logs": {"event": {"status": {1: "Open", 2: "Done"}}}})
        context = func_postgres_schema_context_build(config_postgres_schema=schemas["master"])
        self.assertEqual((context["tables"], context["bulk_blocked"], context["table_blocked"], context["update_blocked"], context["is_truncate_disabled"]), ({"task", "users"}, [["task", 50]], ["task"], ["task"], True))

    def test_routes_allow_only_what_control_lists(self):
        state = SimpleNamespace(cache_postgres_table_rule=func_postgres_table_rule_dict(schemas={"master": {"table": {"task": {"column": self.COLUMNS}, "tag": {"column": self.COLUMNS}}, "control": {"my_read": ["task"], "my_update": ["task"], "my_create": ["tag"], "buffer_limit": {"task": 500}}}, "logs": {"table": {"event": {"column": self.COLUMNS}}, "control": {"admin_create": ["*"], "admin_read": ["*"], "admin_update": ["event"], "admin_delete": ["event"]}}}))
        func_check_table_access(app_state=state, table="task", group="my", action="read")
        for action in ("create", "read", "update", "delete"): func_check_table_access(app_state=state, connection="logs", table="event", group="admin", action=action)    # admin: what its admin_* lists give
        for kwargs, message in (({"table": "task", "group": "my", "action": "delete"}, r"my delete not allowed for table: task \(add \"task\" to control.my_delete in config_postgres_schema_master\)"),
                                ({"table": "task", "group": "public", "action": "read"}, "public read not allowed for table: task"), ({"table": "other", "group": "admin", "action": "read"}, r"admin read not allowed for table: other \(add \"other\" to control.admin_read in config_postgres_schema_master\)"),
                                ({"table": "task", "group": "my", "action": "read", "relation": ["tags,tag,id,task_id"]}, "my read not allowed for table: tag"),
                                ({"connection": "logs", "table": "task", "group": "my", "action": "read"}, "config_postgres_schema_logs")):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(Exception, message) as raised: func_check_table_access(app_state=state, **kwargs)
            self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual((func_buffer_limit(app_state=state, table="task"), func_buffer_limit(app_state=state, table="tag"), func_buffer_limit(app_state=state, table="event", connection="logs")), (500, 100, 100))

    def test_the_gate_applies_ownership_and_column_rules(self):
        state = SimpleNamespace(func_check_table_access=func_check_table_access, cache_postgres_table_rule=func_postgres_table_rule_dict(schemas={"master": {"table": {"task": {"column": self.COLUMNS}}, "control": {"my_read": ["task"], "my_update": ["task"], "my_delete": ["task"], "private_read": ["task"], "public_create": ["task"]}}}))
        self.assertEqual(func_object_access(app_state=state, table="task", group="private", action="read"), ["note"])
        joined = SimpleNamespace(func_check_table_access=lambda **kwargs: None, cache_postgres_table_rule=func_postgres_table_rule_dict(schemas={"master": MASTER}))
        self.assertEqual(func_object_access(app_state=joined, table="test", group="admin", action="read", relation=["created_by_id,users,id,user"]), ["password", "totp_secret", "totp_recovery"])    # a joined table's read_blocked is refused too
        self.assertEqual(func_object_access(app_state=state, table="task", group="my", action="read", ownership_column="assigned_to_id"), [])
        func_object_access(app_state=state, table="task", group="my", action="update", ownership_column="created_by_id", obj_list=[{"id": 1, "note": "x"}])
        for kwargs, message, code in (({"group": "my", "action": "delete", "ownership_column": "assigned_to_id"}, "ownership_column assigned_to_id not allowed for my delete on task", 403),
                                      ({"group": "my", "action": "update", "ownership_column": "created_by_id", "obj_list": [{"status": 2}]}, "status: not writable by my .write_blocked.", 400),
                                      ({"group": "public", "action": "create", "obj_list": [{"note": "x"}, {"deleted_at": "2020-01-01"}]}, "deleted_at: not writable by public .set by Atom.", 400)):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(Exception, message) as raised: func_object_access(app_state=state, table="task", **kwargs)
            self.assertEqual(raised.exception.status_code, code)

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

    def test_users_setup_runs_on_master_only(self):
        class Conn:
            def __init__(self): self.sql = []
            async def execute(self, sql, *args): self.sql.append(sql)
        users = {"users": ["id", "username", "password", "role", "deleted_at", "deactivated_at", "totp_enabled_at", "totp_secret", "totp_last_step", "totp_recovery"]}
        for name, expected in (("master", True), ("telemetry", False)):
            conn, context = Conn(), {**func_postgres_schema_context_build(config_postgres_schema={"table": {"users": {"column": []}}}), "database": name, "triggers": {}}
            asyncio.run(func_postgres_schema_users_init(conn=conn, db_tables=users, catalog=context["catalog"], context=context, root_user_password_hash="hash"))
            with self.subTest(database=name): self.assertEqual(any("INSERT INTO users" in sql for sql in conn.sql), expected)

    def test_users_lists_are_flat_settings_with_id_first(self):
        self.assertEqual(func_postgres_users_access(config_users_token_column=["role", "id"], config_users_private_read_column=["name"], config_users_update_alone_column=["email"]), {"token": ["id", "role"], "private_read": ["id", "name"], "update_alone": ["email"]})
        atom = func_postgres_users_access(config_users_token_column=config.config_users_token_column, config_users_private_read_column=config.config_users_private_read_column, config_users_update_alone_column=config.config_users_update_alone_column)
        self.assertEqual(sorted(atom["token"]), ["deactivated_at", "deleted_at", "id", "id_ext", "permissions", "role", "username"])
        self.assertEqual(sorted(atom["private_read"]), ["created_at", "deactivated_at", "id", "name", "permissions", "role", "username"])
        self.assertEqual(sorted(atom["update_alone"]), ["email", "mobile", "password", "username"])

    def test_atom_tables_keep_their_access(self):
        rules = func_postgres_table_rule_dict(schemas={"master": MASTER})["master"]
        for table in ("users", "config", "webhook", "log_users_password", "otp", "script_run", "queue_job"): self.assertEqual(rules[table]["my"], [])
        self.assertEqual({table for table, rule in rules.items() if "delete_all" in rule["my"]}, {"test", "message", "notification"})
        self.assertEqual({table for table, rule in rules.items() if rule["public"]}, {"test"})
        self.assertEqual((rules["log_api"]["buffer_limit"], rules["log_api"]["retention_day"], rules["otp"]["retention_day"], rules["script_run"]["retention_day"]), (1000, 7, 1, 90))
        self.assertEqual(rules["script_run"]["read_blocked"]["private"], ["started_by", "host", "step", "message", "peak_memory_mb"])
        self.assertEqual({table: rule["read_blocked"]["admin"] for table, rule in rules.items() if table != "*" and rule["read_blocked"]["admin"]}, {"users": ["password", "totp_secret", "totp_recovery"], "api_key": ["key_hash"], "webhook": ["secret"]})
        self.assertEqual((rules["message"]["ownership"]["delete"], rules["log_users_delete"]["ownership"]["read"]), (["created_by_id", "received_by_id"], ["created_by_id", "user_id"]))

    def test_every_group_is_closed_unless_listed_and_outside_tables_may_be_listed(self):
        schemas = {"master": {"table": {"task": {"column": self.COLUMNS}}, "control": {"my_read": ["task"], "admin_read": ["*"], "admin_update": ["task"], "buffer_limit": {"task": 500}}},
                   "crm": {"control": {"public_read": ["product"], "admin_create": ["lead"]}}, "warehouse": {"table": {}, "control": {}, "sql": {}}}
        state = SimpleNamespace(cache_postgres_table_rule=func_postgres_table_rule_dict(schemas=schemas))
        for kwargs in ({"table": "task", "group": "admin", "action": "read"}, {"table": "anything", "group": "admin", "action": "read"}, {"table": "task", "group": "admin", "action": "update"},
                       {"connection": "crm", "table": "product", "group": "public", "action": "read"}, {"connection": "crm", "table": "lead", "group": "admin", "action": "create"}):
            func_check_table_access(app_state=state, **kwargs)    # admin_read ["*"]: every table of master; crm's tables were made outside Atom
        for kwargs, message in (({"table": "task", "group": "admin", "action": "delete"}, r"add \"task\" to control.admin_delete in config_postgres_schema_master"),
                                ({"connection": "crm", "table": "lead", "group": "admin", "action": "read"}, "control.admin_read in config_postgres_schema_crm"),
                                ({"connection": "warehouse", "table": "task", "group": "my", "action": "read"}, "config_postgres_schema_warehouse"),
                                ({"connection": "replica1", "table": "task", "group": "admin", "action": "read"}, "database replica1 has no config_postgres_schema_replica1")):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(Exception, message) as raised: func_check_table_access(app_state=state, **kwargs)
            self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(func_buffer_limit(app_state=state, table="task", connection="replica1"), 100, "no schema: no rules, never master's")
        self.assertFalse(state.cache_postgres_table_rule["crm"]["product"]["is_managed"])
        func_postgres_control_table_check(schemas=schemas, cache_postgres_schema_dict={"master": {"task": {}}, "crm": {"product": {}, "lead": {}}, "warehouse": {}})
        with self.assertRaisesRegex(Exception, r"config_postgres_schema_crm: control.admin_create: lead is not a table of database crm"):
            func_postgres_control_table_check(schemas=schemas, cache_postgres_schema_dict={"master": {"task": {}}, "crm": {"product": {}}})

    def test_wildcard_only_in_admin_lists_and_guards_only_on_managed_tables(self):
        for control, message in (({"public_read": ["*"]}, r"allowed only as \[\"\*\"\] in admin_create, admin_read"), ({"admin_read": ["*", "task"]}, "allowed only as"),
                                 ({"admin_update": ["users"]}, "users not allowed"), ({"row_update_disabled": ["outside"]}, "not in this schema's table part"),
                                 ({"retention_day": {"outside": 5}}, "not in this schema's table part"), ({"public_read": ["bad name"]}, "is not a table name")):
            with self.subTest(control=control), self.assertRaisesRegex(Exception, message): func_postgres_schema_config_validate(config_postgres_schema={"table": {"task": {"column": self.COLUMNS}}, "control": control})
        func_postgres_schema_config_validate(config_postgres_schema={"control": {"private_read": ["outside"], "admin_read": ["*"]}})    # control only: a database Atom doesn't manage


class RoutesNeedingIdTests(unittest.IsolatedAsyncioTestCase):
    SCHEMA = {"reading": {"time": {"datatype": "timestamp with time zone"}, "device": {"datatype": "text"}, "value": {"datatype": "double precision"}}}

    def test_read_without_id_needs_an_order(self):
        with self.assertRaisesRegex(Exception, r"table has no id: pass order") as raised: func_page_keys(order="", columns=self.SCHEMA["reading"])
        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual([key["name"] for key in func_page_keys(order="time desc,device", columns=self.SCHEMA["reading"])], ["time", "device"], "no id added to the order")

    async def test_update_and_delete_need_id(self):
        pool, conn = database()
        with self.assertRaisesRegex(Exception, "table 'reading' has no id: update needs one") as raised:
            await func_postgres_update(client_postgres=pool, client_postgres_conn=None, client_password_hasher=None, cache_postgres_schema=self.SCHEMA, column_regex={}, table="reading", obj_list=[{"value": 1.0}], created_by_id=None)
        self.assertEqual(raised.exception.status_code, 400)
        with self.assertRaisesRegex(Exception, "table 'reading' has no id: delete needs one"):
            await func_postgres_delete(client_postgres=pool, client_postgres_conn=None, cache_postgres_schema=self.SCHEMA, table="reading", ids=[1], created_by_id=None)
        conn.fetch.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
