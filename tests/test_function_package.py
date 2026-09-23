"""Import compatibility checks; no database or optional service is required."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


PACKAGE = Path(__file__).resolve().parents[1] / "function"


class FunctionPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(PACKAGE, self.root / "function", ignore=shutil.ignore_patterns("__pycache__"))

    def write_module(self, filename, content):
        (self.root / "function" / filename).write_text(textwrap.dedent(content))

    def run_python(self, code):
        return subprocess.run(
            [sys.executable, "-c", textwrap.dedent(code)],
            cwd=self.root, capture_output=True, text=True, timeout=30,
        )

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_custom_functions_export_and_register_without_loader_edits(self):
        self.write_module("custom_payments.py", """
            CONSTANT = 42
            def helper(): return "private"
            def func_payment_create(*, amount): return amount
            async def func_payment_read(): return "payment"
        """)
        self.assert_success(self.run_python("""
            import asyncio
            from types import SimpleNamespace
            from function import *
            assert func_payment_create(amount=42) == 42
            assert asyncio.run(func_payment_read()) == "payment"
            assert "CONSTANT" not in globals()
            assert "helper" not in globals()
            app = SimpleNamespace(state=SimpleNamespace())
            func_app_state_add(app=app, data_dict=globals(), prefixes=("func_",))
            assert app.state.func_payment_create(amount=3) == 3
        """))

    def test_duplicate_definitions_report_both_files(self):
        self.write_module("custom_auth.py", "def func_token_encode(): pass\n")
        result = self.run_python("import function")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate function 'func_token_encode'", result.stderr)
        self.assertIn("auth.py", result.stderr)
        self.assertIn("custom_auth.py", result.stderr)

    def test_imported_helpers_do_not_conflict_with_definitions(self):
        self.write_module("custom_parser.py", """
            from .request import func_query_bool_parse
            def func_custom_parse(value):
                return func_query_bool_parse(value)
        """)
        self.assert_success(self.run_python("""
            from function import func_custom_parse, func_query_bool_parse
            from function.request import func_query_bool_parse as original
            assert func_query_bool_parse is original
            assert func_custom_parse("true") is True
        """))

    def test_worker_imports_and_core_registration(self):
        self.assert_success(self.run_python("""
            from types import SimpleNamespace
            from function import *
            from function import func_client_postgres, func_postgres_create
            app = SimpleNamespace(state=SimpleNamespace())
            func_app_state_add(app=app, data_dict=globals(), prefixes=("func_",))
            assert app.state.func_client_postgres is func_client_postgres
            assert app.state.func_postgres_create is func_postgres_create
            assert callable(func_client_postgres)
            assert callable(func_postgres_create)
        """))

    def test_private_modules_are_skipped(self):
        self.write_module("_private.py", "raise RuntimeError('must not load')\n")
        self.assert_success(self.run_python("import function"))

    def test_broken_custom_module_stops_import(self):
        self.write_module("custom_broken.py", "raise RuntimeError('custom load failure')\n")
        result = self.run_python("import function")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("custom load failure", result.stderr)


if __name__ == "__main__":
    unittest.main()
