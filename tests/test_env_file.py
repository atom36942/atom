"""ATOM_ENV_FILE makes func_config_load read that file instead of .env, so a local run never reaches .env's real databases; a name that is not a file stops startup."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from function.config import func_config_load

class EnvFileTests(unittest.TestCase):
    def load(self, env_file):
        """func_config_load in a folder whose .env and tmp/local.env name different databases."""
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"ATOM_ENV_FILE": env_file} if env_file else {}, clear=False):
            os.environ.pop("config_postgres_url_master", None)
            if not env_file: os.environ.pop("ATOM_ENV_FILE", None)
            Path(root, ".env").write_text("config_postgres_url_master=postgresql://real/prod\n")
            Path(root, "tmp").mkdir()
            Path(root, "tmp/local.env").write_text("config_postgres_url_master=postgresql://localhost/local\n")
            os.chdir(root)
            try:
                values = {}
                func_config_load(global_dict=values)
                return values.get("config_postgres_url_dict", {}).get("master")
            finally: os.chdir(cwd)

    def test_without_it_env_is_read(self):
        self.assertEqual(self.load(None), "postgresql://real/prod")

    def test_it_replaces_env(self):
        self.assertEqual(self.load("tmp/local.env"), "postgresql://localhost/local")

    def test_a_missing_file_stops(self):
        with self.assertRaisesRegex(ValueError, "ATOM_ENV_FILE tmp/missing.env not found"): self.load("tmp/missing.env")

if __name__ == "__main__": unittest.main()
