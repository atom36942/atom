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

from script.check import pages_check
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

class StandardTests(unittest.TestCase):
    """The standard score only reports: it names what a project misses and never fails the check."""
    def project(self, files):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        for name, text in {"config_extend.py": "", ".gitignore": ".env\n", **files}.items():
            Path(root, name).parent.mkdir(parents=True, exist_ok=True)
            Path(root, name).write_text(text, encoding="utf-8")
        rules, defaults = standard_check(root=root)
        return {what: missing for what, missing in [*rules, *defaults] if missing}

    def test_outside_a_project_there_is_no_score(self):
        self.assertIsNone(standard_check(root=tempfile.gettempdir() + "/no-such-project"))

    def test_a_project_following_the_standard_misses_nothing(self):
        page = '<meta name="viewport"><style>a{color:var(--text)}</style><script>"/auth/login /my/profile /my/token-refresh /info export_limit theme density My profile Login details Sync Settings Logout"</script>'
        files = {"router_extend/invoice.py": "", "function_extend/invoice.py": "import asyncpg", "docs_extend/invoice.md": "", "tests_extend/test_invoice.py": "", "static_extend/invoice/index.html": page}
        self.assertEqual(self.project(files), {})

    def test_what_is_missing_is_named(self):
        missing = self.project({"router_extend/invoice.py": "import psycopg2", "files_extend/key.txt": "postgresql://app:hunter2@db.example.com/app",
                                "static_extend/invoice.html": '<script src="https://cdn.example.com/x.js"></script><script>fetch("/auth/login")</script>', ".gitignore": ""})
        self.assertEqual(missing["no secret in code or docs (only in .env)"], ["files_extend/key.txt"])
        self.assertEqual(missing["Postgres only through asyncpg"], ["router_extend/invoice.py"])
        self.assertEqual(missing[".env kept out of Git"], [".gitignore"])
        self.assertEqual(missing["each feature has tests_extend/test_<f>.py"], ["invoice"])
        self.assertEqual(missing["pages load no script or style from another site"], ["invoice"])
        self.assertEqual(missing["keeps the login alive (/my/token-refresh)"], ["invoice"])

    def test_the_score_is_in_the_summary_and_never_fails_it(self):
        standard = ([("rule a", [])], [("default b", ["invoice"]), ("default c", [])])
        lines = summary_format(steps=[("startup", True, "")], result=sample_result("test_passes"), seconds=1, standard=standard)
        self.assertIn("standard Rules 1/1, Defaults 1/2", lines[0])
        self.assertIn("  Default: default b: invoice", lines)

if __name__ == "__main__":
    unittest.main()
