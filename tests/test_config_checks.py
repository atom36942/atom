"""Startup validation of PostgreSQL connection settings."""
import unittest
from types import SimpleNamespace

from function import func_check_database_config

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


if __name__ == "__main__":
    unittest.main()
