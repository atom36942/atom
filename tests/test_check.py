"""script.check prints one summary line, then only what needs attention: ruff findings, failing tests with their tracebacks, and grouped skip reasons."""
import re
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from io import StringIO
from pathlib import Path

from script.check import names_check
from script.check import pages_check
from script.check import routes_check
from script.check import rules_check
from script.check import standard_check
from script.check import summary_format

ROOT = Path(__file__).resolve().parents[1]


def sample_result(*names):
    class Sample(unittest.TestCase):    # defined here so test discovery doesn't run it
        def test_passes(self): pass
        def test_fails(self): self.assertEqual(1, 2)
        @unittest.skip("needs a service")
        def test_skipped_a(self): pass
        @unittest.skip("needs a service")
        def test_skipped_b(self): pass
    suite = unittest.TestSuite(Sample(name) for name in names)
    return unittest.TextTestRunner(stream=StringIO(), verbosity=0).run(suite)


class CheckSummaryTests(unittest.TestCase):
    def test_all_green_is_one_line(self):
        lines = summary_format(steps=[("startup", True, ""), ("ruff", True, "")], result=sample_result("test_passes"), seconds=1.23)
        self.assertEqual(lines, ["startup ok · ruff ok · 1 passed · 1.2 s"])

    def test_failures_ruff_and_skips_are_listed_once(self):
        result = sample_result("test_passes", "test_fails", "test_skipped_a", "test_skipped_b")
        text = "\n".join(summary_format(steps=[("startup", False, "Exception: config_api drops 1 route"), ("ruff", False, "x.py:1:1: F401 unused")], result=result, seconds=2))
        self.assertTrue(text.startswith("startup FAILED · ruff FAILED · 1 passed · 1 FAILED · 2 skipped · 2.0 s"), text)
        self.assertIn("F401 unused", text)
        self.assertIn("startup:\nException: config_api drops 1 route", text)
        self.assertEqual(len(re.findall(r"^FAIL: \S+\.Sample\.test_fails$", text, re.MULTILINE)), 1)    # the id's start depends on how discovery was run
        self.assertIn("AssertionError: 1 != 2", text)
        self.assertIn("2 × needs a service", text)
        self.assertNotIn("test_passes", text)


    def test_a_hung_test_is_named_with_where_it_waits(self):
        code = (
            "import time, unittest\n"
            "from script.check import tests_run\n"
            "class Stuck(unittest.TestCase):\n"
            "    def test_waits_forever(self): time.sleep(60)\n"
            "tests_run(suite=unittest.TestSuite([Stuck('test_waits_forever')]), timeout_sec=1)\n"
        )
        done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30, cwd=ROOT)    # noqa: S603 - fixed command
        self.assertEqual(done.returncode, 1)
        self.assertIn("HUNG: __main__.Stuck.test_waits_forever (over 1 s)", done.stderr)
        self.assertIn("in test_waits_forever", done.stderr, "the stack shows where it waits")

    def test_a_skipped_step_says_why(self):
        text = "\n".join(summary_format(steps=[("startup", True, ""), ("pages", None, "node is not installed")], result=sample_result("test_passes"), seconds=1))
        self.assertTrue(text.startswith("startup ok · pages skipped · 1 passed"), text)
        self.assertIn("1 × pages: node is not installed", text)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class PageCheckTests(unittest.TestCase):
    def pages(self, files):
        """pages_check run in a temporary project holding these static_extend/ files."""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            for name, text in files.items():
                Path(folder, "static_extend", name).parent.mkdir(parents=True, exist_ok=True)
                Path(folder, "static_extend", name).write_text(text)
            cwd = os.getcwd()
            os.chdir(folder)
            try: return pages_check()
            finally: os.chdir(cwd)

    def test_valid_scripts_modules_and_non_javascript_pass(self):
        files = {"app.html": "<script>const a = 1;</script>\n<script type=\"module\">import x from '/static/x.js'; export const y = x;</script>\n<script type=\"application/json\">{not javascript</script>\n<script src=\"/static/app/js/app.js\"></script>",
                 "app/js/app.js": "import { a } from './a.js';\nexport const b = a;", "app/js/old.js": "var c = function () { return 1; };"}
        self.assertEqual(self.pages(files), (True, ""))

    def test_a_syntax_error_names_the_page_and_its_line(self):
        status, output = self.pages({"app.html": "<html>\n<body>\n<script>\nconst ok = 1;\nconst broken = ;\n</script>"})
        self.assertFalse(status)
        self.assertIn("static_extend/app.html:5", output, "the page's own line number")
        self.assertIn("SyntaxError", output)

    def test_without_node_the_step_is_skipped(self):
        with patch("script.check.shutil.which", return_value=None): self.assertEqual(self.pages({})[0], None)

class NamesCheckTests(unittest.TestCase):
    def check(self, files):
        """names_check run in a temporary project holding these files."""
        with tempfile.TemporaryDirectory() as root:
            for name, text in {"config_extend.py": "", **files}.items():
                Path(root, name).parent.mkdir(parents=True, exist_ok=True)
                Path(root, name).write_text(text)
            return names_check(root=root)

    def test_calls_to_defined_functions_pass(self):
        status, _ = self.check({"function/user.py": "async def func_user_read(): pass\n", "function_extend/shop.py": "def func_shop_total(): pass\n", "router_extend/shop.py": "x = request.app.state.func_user_read\ny = app_state.func_shop_total\n"})
        self.assertIs(status, True)

    def test_an_unknown_function_is_named_with_its_line(self):
        status, output = self.check({"function/user.py": "def func_user_read(): pass\n", "router_extend/shop.py": "\nx = request.app.state.func_user_get\n"})
        self.assertIs(status, False)
        self.assertIn("router_extend/shop.py:2: func_user_get", output)

    def test_outside_a_project_the_step_is_skipped(self):
        with tempfile.TemporaryDirectory() as root: self.assertIsNone(names_check(root=root)[0])


class RoutesCheckTests(unittest.TestCase):
    API = {"/": {}, "/static": {}, "/page/{name}": {}, "/info": {}, "/admin/object-read": {}, "/admin/postgres-query-ai": {}, "/my/profile": {}, "/shop/order-read": {}}

    def check(self, page):
        """routes_check run in a temporary project whose one page holds this text."""
        with tempfile.TemporaryDirectory() as root:
            Path(root, "config_extend.py").write_text("")
            Path(root, "static_extend").mkdir()
            Path(root, "static_extend/shop.html").write_text(page)
            return routes_check(root=root, config_api=self.API)

    def test_routes_queries_values_files_and_other_hosts_pass(self):
        page = r"""<a href="/page/shop">x</a><script src="/static/shop/app.js"></script><script>
fetch("/info"); fetch('/my/profile'); fetch(`/admin/object-read?table=${t}`); fetch("/admin/object-read?table=" + t)
fetch(`/page/${name}`); fetch(`/admin/object-read${q ? `?${qs(q)}` : ""}`); fetch("/shop/order-read#top")
fetch("https://api.other.com/admin/x"); const re = /a\/b/; const s = "a / b"; const r = "/"; fetch("/static/shop/x.json")
</script>"""
        self.assertEqual(self.check(page), (True, ""))

    def test_a_renamed_route_is_named_with_its_line(self):
        status, output = self.check('<script>\nfetch("/admin/postgres-query-generator-ai", { method: "POST" })\n</script>')
        self.assertIs(status, False)
        self.assertIn("static_extend/shop.html:2: /admin/postgres-query-generator-ai", output)

    def test_a_path_built_from_parts_or_an_unknown_project_route_fails(self):
        for page in ['fetch("/admin/" + view)', "fetch(`/admin/${view}`)", 'fetch("/shop/order-delete")', 'fetch("/my/profile/x")']:
            with self.subTest(page=page): self.assertIs(self.check(f"<script>{page}</script>")[0], False)

    def test_outside_a_project_the_step_is_skipped(self):
        with tempfile.TemporaryDirectory() as root: self.assertIsNone(routes_check(root=root, config_api=self.API)[0])


def project_make(test, files):
    """A throwaway project folder with files ({path: text}), removed after the test."""
    root = Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, root, ignore_errors=True)
    for name, text in {"config_extend.py": "", ".gitignore": ".env\n", **files}.items():
        Path(root, name).parent.mkdir(parents=True, exist_ok=True)
        Path(root, name).write_text(text, encoding="utf-8")
    return root


class RulesTests(unittest.TestCase):
    """AGENTS.md's Enforced code rules fail the check, each break named with its file and line."""
    def test_outside_a_project_the_step_is_skipped(self):
        with tempfile.TemporaryDirectory() as root: self.assertIsNone(rules_check(root=root)[0])

    def test_a_project_following_the_rules_passes(self):
        files = {"function_extend/invoice.py": "import asyncpg\nasync def func_invoice_read(*, client_postgres): return await client_postgres.fetch('SELECT 1')",
                 "router_extend/invoice.py": "async def invoice_read(request):\n    user_id = request.state.user['id']\n    row = {'role': 2}\n    return row['role'], row.get('permissions')",
                 "script_extend/invoice_sync.py": "import asyncpg\nasync def main(): return await asyncpg.connect('')"}
        self.assertEqual(rules_check(root=project_make(self, files)), (True, ""))

    def test_each_break_is_named_with_its_line(self):
        files = {"function_extend/invoice.py": "import httpx\nimport redis.asyncio as redis\nclient = httpx.AsyncClient()\npool = redis.Redis.from_url('')",
                 "router_extend/invoice.py": "import psycopg2\ndef read(request):\n    if request.state.user['role'] != 2: return\n    return request.state.user.get('permissions')",
                 "files_extend/key.txt": "\npostgresql://app:hunter2@db.example.com/app", ".gitignore": ""}
        status, output = rules_check(root=project_make(self, files))
        self.assertIs(status, False)
        for line in ["function_extend/invoice.py:3: httpx.AsyncClient()", "function_extend/invoice.py:4: redis.Redis.from_url()", "router_extend/invoice.py:1: Postgres only through asyncpg (no psycopg2)", "router_extend/invoice.py:3: checks the user's role", "router_extend/invoice.py:4: checks the user's permissions", "files_extend/key.txt:2: a secret in code", ".gitignore: .env is not listed"]:
            self.assertIn(line, output)


class StandardTests(unittest.TestCase):
    """The standard score only reports: it names which Defaults a project misses and never fails the check."""
    def project(self, files):
        return {what: missing for what, missing in standard_check(root=project_make(self, files)) if missing}

    def test_outside_a_project_there_is_no_score(self):
        self.assertIsNone(standard_check(root=tempfile.gettempdir() + "/no-such-project"))

    def test_a_project_following_the_standard_misses_nothing(self):
        page = '<meta name="viewport"><script>"/auth/login /my/profile /my/token-refresh /info export_limit"</script>'
        files = {"router_extend/invoice.py": "", "function_extend/invoice.py": "import asyncpg", "docs_extend/invoice.md": "", "tests_extend/test_invoice.py": "", "static_extend/invoice/index.html": page}
        self.assertEqual(self.project(files), {})

    def test_what_is_missing_is_named(self):
        missing = self.project({"router_extend/invoice.py": "", "static_extend/invoice.html": '<script src="https://cdn.example.com/x.js"></script><script>fetch("/auth/login")</script>'})
        self.assertEqual(missing["each feature has tests_extend/test_<f>.py"], ["invoice"])
        self.assertEqual(missing["pages load no script or style from another site"], ["invoice"])
        self.assertEqual(missing["keeps the login alive (/my/token-refresh)"], ["invoice"])

    def test_the_score_is_in_the_summary_and_never_fails_it(self):
        standard = [("default b", ["invoice"]), ("default c", [])]
        lines = summary_format(steps=[("startup", True, "")], result=sample_result("test_passes"), seconds=1, standard=standard)
        self.assertIn("standard Defaults 1/2", lines[0])
        self.assertIn("  default b: invoice", lines)

if __name__ == "__main__":
    unittest.main()
