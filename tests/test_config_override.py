"""Loading config_* values from the environment."""
import os
import tempfile
import unittest
from unittest.mock import patch

from function.config import func_config_load


def override(env, **config):
    """Run the loader from an empty temp cwd (so no real .env is read) with only the given environment."""
    global_dict = {"config_postgres_url_dict": {}, "config_redis_url_dict": {}, "config_clickhouse_url_dict": {}, "config_mssql_url_dict": {}} | config
    previous_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as workdir, patch.dict(os.environ, env, clear=True):
        os.chdir(workdir)
        try: func_config_load(global_dict=global_dict)
        finally: os.chdir(previous_cwd)
    return global_dict


class ConfigOverrideTests(unittest.TestCase):
    def test_values_are_parsed_by_the_default_type(self):
        result = override({"config_is_prod": "false", "config_otp_length": "8", "config_cors_allow_origins": '["https://a.com"]', "config_sentry_dsn": "https://x"},
                          config_is_prod=True, config_otp_length=6, config_cors_allow_origins=[], config_sentry_dsn=None)
        self.assertEqual((result["config_is_prod"], result["config_otp_length"], result["config_cors_allow_origins"], result["config_sentry_dsn"]),
                         (False, 8, ("https://a.com",), "https://x"))

    def test_decimal_settings_are_parsed_as_numbers(self):
        result = override({"config_sentry_traces_sample_rate": "0.2"}, config_sentry_traces_sample_rate=0.05)
        self.assertEqual(result["config_sentry_traces_sample_rate"], 0.2)
        with self.assertRaisesRegex(ValueError, "invalid number for config_sentry_traces_sample_rate"):
            override({"config_sentry_traces_sample_rate": "high"}, config_sentry_traces_sample_rate=0.05)

    def test_invalid_boolean_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid boolean value for config_is_prod"):
            override({"config_is_prod": "maybe"}, config_is_prod=True)

    def test_uppercase_keys_are_read(self):
        self.assertEqual(override({"CONFIG_OTP_LENGTH": "4"}, config_otp_length=6)["config_otp_length"], 4)

    def test_postgres_urls_fill_the_named_dict(self):
        result = override({"config_postgres_url_master": "postgresql://m", "config_postgres_url_reports": "postgresql://r"})
        self.assertEqual(result["config_postgres_url_dict"], {"master": "postgresql://m", "reports": "postgresql://r"})
        self.assertNotIn("config_postgres_url_master", result)

    def test_redis_urls_fill_the_named_dict_including_project_names(self):
        result = override({"config_redis_url_api_response": "redis://a", "CONFIG_REDIS_URL_QUEUE": "redis://q", "config_redis_url_sessions": "redis://s"})
        self.assertEqual(result["config_redis_url_dict"], {"api_response": "redis://a", "queue": "redis://q", "sessions": "redis://s"})
        self.assertNotIn("config_redis_url_api_response", result)

    def test_url_with_empty_name_is_rejected(self):
        for key in ("config_postgres_url_", "config_redis_url_", "config_clickhouse_url_", "config_mssql_url_"):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, f"{key} needs a name"):
                override({key: "x"})

    def test_options_file_paths_load_into_lists(self):
        with tempfile.TemporaryDirectory() as folder:
            txt, js = os.path.join(folder, "city.txt"), os.path.join(folder, "currency.json")
            with open(txt, "w") as file: file.write("Pune\n\n Delhi \n")
            with open(js, "w") as file: file.write('["INR", "USD"]')
            result = override({}, config_options={"gender": ["male"], "city": txt, "currency": js})
        self.assertEqual(result["config_options"], {"gender": ["male"], "city": ["Pune", "Delhi"], "currency": ["INR", "USD"]})

    def test_options_bad_file_stops_loading(self):
        with tempfile.TemporaryDirectory() as folder:
            bad_json, not_list = os.path.join(folder, "a.json"), os.path.join(folder, "b.json")
            with open(bad_json, "w") as file: file.write("[")
            with open(not_list, "w") as file: file.write("{}")
            for path, message in ((os.path.join(folder, "missing.txt"), "file not found"), (os.path.join(folder, "x.csv"), "use a .txt or .json"), (bad_json, "invalid JSON"), (not_list, "must hold a JSON list")):
                with self.subTest(message=message), self.assertRaisesRegex(ValueError, f"config_options 'city': .*{message}|config_options 'city': {message}"):
                    override({}, config_options={"city": path})

    def test_clickhouse_urls_fill_the_named_dict(self):
        result = override({"config_clickhouse_url_master": "clickhouse://m", "CONFIG_CLICKHOUSE_URL_EVENTS": "clickhouse://e"})
        self.assertEqual(result["config_clickhouse_url_dict"], {"master": "clickhouse://m", "events": "clickhouse://e"})
        self.assertNotIn("config_clickhouse_url_master", result)

    def test_mssql_urls_fill_the_named_dict(self):
        result = override({"config_mssql_url_master": "DRIVER={ODBC Driver 18 for SQL Server};SERVER=m", "CONFIG_MSSQL_URL_ERP": "SERVER=e"})
        self.assertEqual(result["config_mssql_url_dict"], {"master": "DRIVER={ODBC Driver 18 for SQL Server};SERVER=m", "erp": "SERVER=e"})
        self.assertNotIn("config_mssql_url_master", result)

    def test_unknown_config_keys_are_added_with_a_parsed_type(self):
        result = override({"config_new_flag": "yes", "config_new_limit": "-3", "config_new_list": "[1, 2]", "config_new_text": "hello", "other_key": "x"})
        self.assertEqual((result["config_new_flag"], result["config_new_limit"], result["config_new_list"], result["config_new_text"]), (True, -3, (1, 2), "hello"))
        self.assertNotIn("other_key", result)


if __name__ == "__main__":
    unittest.main()
