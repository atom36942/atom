"""Startup validation of PostgreSQL connection settings."""
import unittest
from types import SimpleNamespace

from function import func_check_database_config, func_check_log_api_table, func_check_runtime_config

URL = "postgresql://user@localhost:5432/db"


def state(**changes):
    return SimpleNamespace(**({"config_postgres_pool_min_size": 1, "config_postgres_pool_max_size": 5, "config_postgres_url_dict": {},
                               "config_postgres_db_log_api": "master"} | changes))


class DatabaseConfigCheckTests(unittest.TestCase):
    def test_valid_setups_pass(self):
        for url_dict in ({}, {"master": URL}, {"master": URL, "logs": URL}):
            with self.subTest(url_dict=url_dict):
                func_check_database_config(app_state=state(config_postgres_url_dict=url_dict))

    def test_old_single_url_setting_is_rejected_with_rename_hint(self):
        with self.assertRaisesRegex(Exception, "config_postgres_url was renamed to config_postgres_url_master"):
            func_check_database_config(app_state=state(config_postgres_url=URL, config_postgres_url_dict={"master": URL}))

    def test_master_is_required_once_any_database_is_set(self):
        with self.assertRaisesRegex(Exception, "config_postgres_url_master is required"):
            func_check_database_config(app_state=state(config_postgres_url_dict={"logs": URL}))

    def test_log_api_database_must_exist(self):
        with self.assertRaisesRegex(Exception, "config_postgres_db_log_api 'audit' not found"):
            func_check_database_config(app_state=state(config_postgres_url_dict={"master": URL}, config_postgres_db_log_api="audit"))

    def test_log_database_must_have_log_api_table(self):
        log_state = lambda schema, **changes: SimpleNamespace(**({"config_postgres_db_log_api": "logs", "config_is_read_only": False, "client_postgres_dict": {"master": object(), "logs": object()}, "cache_postgres_schema_dict": {"master": {}, "logs": schema}} | changes))
        with self.assertRaisesRegex(Exception, "config_postgres_db_log_api 'logs' has no log_api table"):
            func_check_log_api_table(app_state=log_state({"other": {}}))
        func_check_log_api_table(app_state=log_state({"log_api": {}}))
        func_check_log_api_table(app_state=log_state({}, config_is_read_only=True))    # no logging in read-only mode
        func_check_log_api_table(app_state=log_state({}, client_postgres_dict={}))    # no databases configured

    def test_buffer_rows_max_must_be_an_integer_of_at_least_1000(self):
        limits = {key: 100 for key in ("config_query_runner_read_limit", "config_query_runner_export_limit", "config_sql_read_limit_default", "config_sql_read_limit_max", "config_sql_read_relation_fetch_limit_max", "config_postgres_buffer_flush_auto_sec", "config_inmemory_cache_cleanup_auto_sec")}
        runtime_state = lambda value: SimpleNamespace(**limits, config_otp_retention_day=None, config_log_api_retention_day=None, config_buffer_limit_default=100, config_buffer_rows_max=value)
        for value in (1000, 100000):
            func_check_runtime_config(app_state=runtime_state(value))
        for value in (999, "100000", True):
            with self.subTest(value=value), self.assertRaisesRegex(Exception, "config_buffer_rows_max must be an integer of at least 1000"):
                func_check_runtime_config(app_state=runtime_state(value))


if __name__ == "__main__":
    unittest.main()
