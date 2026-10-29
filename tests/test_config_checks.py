"""Startup validation of PostgreSQL connection settings."""
import unittest
from types import SimpleNamespace

from fastapi import FastAPI

from function import func_check_api_config
from function import func_check_config_extend_alias
from function import func_check_config_extend_keeps_atom
from function import func_check_database_config
from function import func_check_log_api_table
from function import func_check_runtime_config

URL = "postgresql://user@localhost:5432/db"


def state(**changes):
    return SimpleNamespace(**({"config_postgres_pool_min_size": 1, "config_postgres_pool_max_size": 5, "config_postgres_url_dict": {},
                               "config_postgres_db_log_api": "master"} | changes))


class ConfigExtendKeepsAtomTests(unittest.TestCase):
    BASE = SimpleNamespace(config_api={"/health": {"id": 1}, "/info": {"id": 2}}, config_postgres={"extension": ["postgis", "pg_trgm"], "table": {"users": [], "log_api": []}, "control": {"is_index_drop": True}, "sql": {}},
                           config_column_int_mapping={"blob": {"type": {1: "File", 2: "Presigned Url"}}, "log_users_delete": {"worker_status": {None: "Pending", 1: "Processing"}}})

    def check(self, **extend):
        func_check_config_extend_keeps_atom(config_module=self.BASE, config_extend_module=SimpleNamespace(**extend))

    def test_extending_any_way_passes(self):
        postgres = {**self.BASE.config_postgres, "table": {**self.BASE.config_postgres["table"]}}    # Atom's top level and tables, as config_extend.py writes it
        postgres["table"].update({"task": [], "users": [{"name": "id"}]})    # a new table, and Atom's users columns changed
        self.check(config_api={**self.BASE.config_api, "/health": {"id": 1, "is_active": False}, "/task": {"id": 200}}, config_postgres=postgres)
        self.check(config_api=dict(self.BASE.config_api))    # a copy works as well as **base
        self.check(config_options={})    # other dicts are not checked
        self.check()
        func_check_config_extend_keeps_atom(config_module=self.BASE, config_extend_module=None)

    def test_postgres_keeps_every_part_and_entry_atom_defines(self):
        base = self.BASE.config_postgres
        self.check(config_postgres={**base, "extension": [*base["extension"], "hstore"], "control": {"is_index_drop": False, "is_new": True}, "table": {**base["table"], "task": []}})    # values change, additions are free
        with self.assertRaisesRegex(Exception, r"config_postgres drops 4 of Atom's entries \(extension, control, sql, table.log_api\)"):
            self.check(config_postgres={"table": {"users": []}})    # written from scratch: Atom's parts are gone
        with self.assertRaisesRegex(Exception, r"drops 2 of Atom's entries \(extension.pg_trgm, control.is_index_drop\)"):
            self.check(config_postgres={**base, "extension": ["postgis"], "control": {}})

    def test_int_mapping_keeps_atom_codes_but_labels_and_additions_are_free(self):
        self.check(config_column_int_mapping={**self.BASE.config_column_int_mapping, "blob": {"type": {1: "Upload", 2: "Signed link", 3: "Mine"}}, "users": {"role": {1: "Admin"}}})
        with self.assertRaisesRegex(Exception, r"config_column_int_mapping drops 2 of Atom's codes \(blob.type 2, log_users_delete.worker_status None\); fix: keep Atom's codes, labels may change"):
            self.check(config_column_int_mapping={"blob": {"type": {1: "File"}}, "log_users_delete": {"worker_status": {1: "Processing"}}})
        with self.assertRaisesRegex(Exception, r"drops 4 of Atom's codes"):
            self.check(config_column_int_mapping={"blob": ["not", "a", "dict"]})    # an odd value gets the same clear message

    def test_dropping_atom_routes_or_tables_stops_startup(self):
        with self.assertRaisesRegex(Exception, r"config_api drops 2 of Atom's routes \(/health, /info\); fix: \{\*\*base_config_api, \.\.\.\}"):
            self.check(config_api={"/task": {"id": 200}})
        with self.assertRaisesRegex(Exception, r"config_postgres drops 1 of Atom's entries \(table.log_api\); fix: \{\*\*base_config_postgres, \"table\": \{\*\*base_config_postgres\[\"table\"\], \.\.\.\}\}"):
            self.check(config_postgres={**self.BASE.config_postgres, "table": {"users": [], "task": []}})


class ConfigExtendAliasTests(unittest.TestCase):
    def test_alias_starting_with_config_is_rejected(self):
        base = SimpleNamespace(config_options={"gender": []}, config_is_prod=True)
        with self.assertRaisesRegex(Exception, "config_options_base is an alias of config_options; name it base_config_options"):
            func_check_config_extend_alias(config_module=base, config_extend_module=SimpleNamespace(config_options_base=base.config_options))

    def test_normal_extend_names_pass(self):
        base = SimpleNamespace(config_options={"gender": []}, config_is_prod=True)
        extend = SimpleNamespace(base_config_options=base.config_options, config_options={**base.config_options}, config_new_flag=True, config_new_list=[1])
        func_check_config_extend_alias(config_module=base, config_extend_module=extend)
        func_check_config_extend_alias(config_module=base, config_extend_module=SimpleNamespace(config_options=base.config_options))
        func_check_config_extend_alias(config_module=base, config_extend_module=None)


class DatabaseConfigCheckTests(unittest.TestCase):
    def test_valid_setups_pass(self):
        for url_dict in ({}, {"master": URL}, {"master": URL, "logs": URL}):
            with self.subTest(url_dict=url_dict):
                func_check_database_config(app_state=state(config_postgres_url_dict=url_dict))

    def test_url_without_name_suffix_is_rejected(self):
        for key in ("config_postgres_url", "config_redis_url", "config_clickhouse_url", "config_mssql_url"):
            with self.subTest(key=key), self.assertRaisesRegex(Exception, f"{key} needs a name suffix"):
                func_check_database_config(app_state=state(**{key: "x"}))

    def test_master_is_required_once_any_database_is_set(self):
        with self.assertRaisesRegex(Exception, "config_postgres_url_master is required"):
            func_check_database_config(app_state=state(config_postgres_url_dict={"logs": URL}))

    def test_clickhouse_dict_names_and_urls_are_checked(self):
        func_check_database_config(app_state=state(config_clickhouse_url_dict={"master": "clickhouse://localhost", "events": "https://ch:8443"}))
        with self.assertRaisesRegex(Exception, "invalid config_clickhouse_url_dict name"):
            func_check_database_config(app_state=state(config_clickhouse_url_dict={"bad-name": "clickhouse://localhost"}))
        with self.assertRaisesRegex(Exception, "must be dict"):
            func_check_database_config(app_state=state(config_clickhouse_url_dict="clickhouse://localhost"))

    def test_mssql_dict_names_are_checked(self):
        func_check_database_config(app_state=state(config_mssql_url_dict={"master": "SERVER=m", "erp": "SERVER=e"}))
        with self.assertRaisesRegex(Exception, "invalid config_mssql_url_dict name"):
            func_check_database_config(app_state=state(config_mssql_url_dict={"1erp": "SERVER=e"}))

    def test_log_api_database_must_exist(self):
        with self.assertRaisesRegex(Exception, "config_postgres_db_log_api 'audit' not found"):
            func_check_database_config(app_state=state(config_postgres_url_dict={"master": URL}, config_postgres_db_log_api="audit"))
        for off in (None, ""):    # API logging off: no log database to find
            func_check_database_config(app_state=state(config_postgres_url_dict={"master": URL}, config_postgres_db_log_api=off))

    def test_log_database_must_have_log_api_table(self):
        log_state = lambda schema, **changes: SimpleNamespace(**({"config_postgres_db_log_api": "logs", "config_is_read_only": False, "client_postgres_dict": {"master": object(), "logs": object()}, "cache_postgres_schema_dict": {"master": {}, "logs": schema}} | changes))
        with self.assertRaisesRegex(Exception, "config_postgres_db_log_api 'logs' has no log_api table"):
            func_check_log_api_table(app_state=log_state({"other": {}}))
        func_check_log_api_table(app_state=log_state({"log_api": {}}))
        func_check_log_api_table(app_state=log_state({}, config_is_read_only=True))    # no logging in read-only mode
        func_check_log_api_table(app_state=log_state({}, client_postgres_dict={}))    # no databases configured

    def test_buffer_rows_max_must_be_an_integer_of_at_least_1000(self):
        limits = dict.fromkeys(("config_query_runner_read_limit", "config_export_limit", "config_sql_read_limit_default", "config_sql_read_limit_max", "config_sql_read_relation_fetch_limit_max", "config_postgres_buffer_flush_auto_sec", "config_inmemory_cache_cleanup_auto_sec", "config_uvicorn_workers"), 100)
        runtime_state = lambda value: SimpleNamespace(**limits, config_otp_retention_day=None, config_log_api_retention_day=None, config_buffer_limit_default=100, config_buffer_rows_max=value)
        for value in (1000, 100000):
            func_check_runtime_config(app_state=runtime_state(value))
        for value in (999, "100000", True):
            with self.subTest(value=value), self.assertRaisesRegex(Exception, "config_buffer_rows_max must be an integer of at least 1000"):
                func_check_runtime_config(app_state=runtime_state(value))


class ApiIdCheckTests(unittest.TestCase):
    def app(self, api_id):
        app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
        def project(): pass
        project.__module__ = "router_extend.feature"
        app.get("/x")(project)
        app.state.config_api = {"/x": {"id": api_id, "is_token": False}}
        app.state.config_uvicorn_workers = 1
        return app

    def test_project_routes_use_ids_from_200(self):
        func_check_api_config(app=self.app(200))
        with self.assertRaisesRegex(Exception, "project routes use ids from 200"):
            func_check_api_config(app=self.app(199))


class WebsocketConfigCheckTests(unittest.TestCase):
    def app(self, socket_cfg, http_cfg=None):
        app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
        app.get("/x")(lambda: None)
        async def socket(websocket): pass
        app.websocket("/ws")(socket)
        app.state.config_api = {"/x": http_cfg or {"id": 1, "is_token": False}, "/ws": socket_cfg}
        app.state.config_uvicorn_workers = 1
        return app

    def test_websocket_entry_takes_only_id_and_is_active(self):
        func_check_api_config(app=self.app({"id": 2}))
        func_check_api_config(app=self.app({"id": 2, "is_active": False}))
        for key, value in (("is_token", False), ("user_check_role", {"mode": "token", "roles": [1]}), ("rate_limit", {"mode": "inmemory", "limit": 5, "window_sec": 60})):
            with self.subTest(key=key), self.assertRaisesRegex(Exception, f"websocket routes accept only id and is_active \\({key} is HTTP-only"):
                func_check_api_config(app=self.app({"id": 2, key: value}))

    def test_is_log_api_must_be_a_boolean(self):
        func_check_api_config(app=self.app({"id": 2}, http_cfg={"id": 1, "is_token": False, "is_log_api": False}))
        with self.assertRaisesRegex(Exception, "invalid /x is_log_api: expected bool"):
            func_check_api_config(app=self.app({"id": 2}, http_cfg={"id": 1, "is_token": False, "is_log_api": "no"}))

    def test_http_entry_still_needs_is_token(self):
        with self.assertRaisesRegex(Exception, "/x missing required key: is_token"):
            func_check_api_config(app=self.app({"id": 2}, http_cfg={"id": 1}))


class WorkerConfigCheckTests(unittest.TestCase):
    def app(self, workers, cfg):
        app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
        app.get("/x")(lambda: None)
        app.state.config_api = {"/x": {"id": 1, "is_token": False, **cfg}}
        app.state.config_uvicorn_workers = workers
        app.state.config_redis_url_dict = {"api_response": "redis://localhost", "ratelimiter": "redis://localhost", "user_state": "redis://localhost"}
        return app

    def test_inmemory_is_rejected_only_with_several_workers(self):
        for cfg, label in (({"rate_limit": {"mode": "inmemory", "limit": 5, "window_sec": 60}}, "/x rate_limit"),
                           ({"cache": {"mode": "inmemory", "ttl_sec": 10}}, "/x cache"),
                           ({"user_check_role": {"mode": "inmemory", "roles": [1]}}, "/x user_check_role"),
                           ({"user_check_deleted": {"mode": "inmemory"}}, "/x user_check_deleted")):
            with self.subTest(label=label):
                func_check_api_config(app=self.app(1, cfg))
                with self.assertRaisesRegex(Exception, f"config_uvicorn_workers=4 .*{label}"):
                    func_check_api_config(app=self.app(4, cfg))

    def test_redis_modes_need_their_role_in_the_redis_dict(self):
        for cfg, role in (({"cache": {"mode": "redis", "ttl_sec": 10}}, "api_response"), ({"rate_limit": {"mode": "redis", "limit": 5, "window_sec": 60}}, "ratelimiter"), ({"user_check_role": {"mode": "redis", "roles": [1]}}, "user_state")):
            with self.subTest(role=role):
                app = self.app(1, cfg)
                app.state.config_redis_url_dict = {"sessions": "redis://localhost"}    # a project's own Redis does not satisfy a role
                with self.assertRaisesRegex(Exception, f"config_redis_url_{role} is missing"):
                    func_check_api_config(app=app)
                app.state.config_redis_url_dict = {role: "http://not-redis"}
                with self.assertRaisesRegex(Exception, f"config_redis_url_{role} must be a valid Redis URL"):
                    func_check_api_config(app=app)
                app.state.config_redis_url_dict = {role: "redis://localhost"}
                func_check_api_config(app=app)

    def test_shared_modes_pass_with_several_workers(self):
        func_check_api_config(app=self.app(4, {"rate_limit": {"mode": "redis", "limit": 5, "window_sec": 60}, "cache": {"mode": "redis", "ttl_sec": 10}, "user_check_role": {"mode": "realtime", "roles": [1]}, "user_check_deleted": {"mode": "token"}}))

    def test_production_rejects_short_token_secret(self):
        limits = dict.fromkeys(("config_query_runner_read_limit", "config_export_limit", "config_sql_read_limit_default", "config_sql_read_limit_max", "config_sql_read_relation_fetch_limit_max", "config_postgres_buffer_flush_auto_sec", "config_inmemory_cache_cleanup_auto_sec", "config_uvicorn_workers"), 100)
        check = lambda **values: func_check_runtime_config(app_state=SimpleNamespace(**limits, config_otp_retention_day=None, config_log_api_retention_day=None, config_buffer_limit_default=100, config_buffer_rows_max=1000, **values))
        for secret in ("short", 123456, "x" * 31):
            with self.subTest(secret=secret), self.assertRaisesRegex(Exception, "at least 32 bytes"):
                check(config_is_prod=True, config_token_secret_key=secret)
        check(config_is_prod=True, config_token_secret_key="x" * 32)
        check(config_is_prod=True, config_token_secret_key=None)
        check(config_is_prod=False, config_token_secret_key="short")

    def test_keep_alive_must_be_a_positive_integer(self):
        limits = dict.fromkeys(("config_query_runner_read_limit", "config_export_limit", "config_sql_read_limit_default", "config_sql_read_limit_max", "config_sql_read_relation_fetch_limit_max", "config_postgres_buffer_flush_auto_sec", "config_inmemory_cache_cleanup_auto_sec", "config_uvicorn_workers"), 100)
        check = lambda value: func_check_runtime_config(app_state=SimpleNamespace(**limits, config_otp_retention_day=None, config_log_api_retention_day=None, config_buffer_limit_default=100, config_buffer_rows_max=1000, config_uvicorn_timeout_keep_alive_sec=value))
        for value in (0, True, "75", 1.5):
            with self.subTest(value=value), self.assertRaisesRegex(Exception, "config_uvicorn_timeout_keep_alive_sec"): check(value)
        check(75)

    def test_workers_must_be_a_positive_integer(self):
        limits = dict.fromkeys(("config_query_runner_read_limit", "config_export_limit", "config_sql_read_limit_default", "config_sql_read_limit_max", "config_sql_read_relation_fetch_limit_max", "config_postgres_buffer_flush_auto_sec", "config_inmemory_cache_cleanup_auto_sec"), 100)
        for value in (0, True, None):
            with self.subTest(value=value), self.assertRaisesRegex(Exception, "config_uvicorn_workers"):
                func_check_runtime_config(app_state=SimpleNamespace(**limits, config_uvicorn_workers=value, config_otp_retention_day=None, config_log_api_retention_day=None, config_buffer_limit_default=100, config_buffer_rows_max=1000))


if __name__ == "__main__":
    unittest.main()
