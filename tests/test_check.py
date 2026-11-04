"""script.check prints one summary line, then only what needs attention: ruff findings, failing tests with their tracebacks, and grouped skip reasons."""
import re
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path

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

if __name__ == "__main__":
    unittest.main()
