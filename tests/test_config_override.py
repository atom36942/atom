"""Loading config_* values from the environment."""
import os
import tempfile
import unittest
from unittest.mock import patch

from function.config import func_config_load_env


def override(env, **config):
    """Run the loader from an empty temp cwd (so no real .env is read) with only the given environment."""
    global_dict = {"config_postgres_url_dict": {}} | config
    previous_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as workdir, patch.dict(os.environ, env, clear=True):
        os.chdir(workdir)
        try: func_config_load_env(global_dict=global_dict)
        finally: os.chdir(previous_cwd)
    return global_dict


class ConfigOverrideTests(unittest.TestCase):
    def test_values_are_parsed_by_the_default_type(self):
        result = override({"config_is_prod": "false", "config_otp_length": "8", "config_cors_allow_origins": '["https://a.com"]', "config_sentry_dsn": "https://x"},
                          config_is_prod=True, config_otp_length=6, config_cors_allow_origins=[], config_sentry_dsn=None)
        self.assertEqual((result["config_is_prod"], result["config_otp_length"], result["config_cors_allow_origins"], result["config_sentry_dsn"]),
                         (False, 8, ("https://a.com",), "https://x"))

    def test_invalid_boolean_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid boolean value for config_is_prod"):
            override({"config_is_prod": "maybe"}, config_is_prod=True)

    def test_uppercase_keys_are_read(self):
        self.assertEqual(override({"CONFIG_OTP_LENGTH": "4"}, config_otp_length=6)["config_otp_length"], 4)

    def test_postgres_urls_fill_the_named_dict(self):
        result = override({"config_postgres_url_master": "postgresql://m", "config_postgres_url_reports": "postgresql://r"})
        self.assertEqual(result["config_postgres_url_dict"], {"master": "postgresql://m", "reports": "postgresql://r"})
        self.assertNotIn("config_postgres_url_master", result)

    def test_unknown_config_keys_are_added_with_a_parsed_type(self):
        result = override({"config_new_flag": "yes", "config_new_limit": "-3", "config_new_list": "[1, 2]", "config_new_text": "hello", "other_key": "x"})
        self.assertEqual((result["config_new_flag"], result["config_new_limit"], result["config_new_list"], result["config_new_text"]), (True, -3, (1, 2), "hello"))
        self.assertNotIn("other_key", result)


if __name__ == "__main__":
    unittest.main()
