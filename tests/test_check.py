"""script.check prints one summary line, then only what needs attention: ruff findings, failing tests with their tracebacks, and grouped skip reasons."""
import unittest
from io import StringIO

from script.check import summary_format


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
        lines = summary_format(is_ruff_ok=True, ruff_output="", result=sample_result("test_passes"), seconds=1.23)
        self.assertEqual(lines, ["ruff ok · 1 passed · 1.2 s"])

    def test_failures_ruff_and_skips_are_listed_once(self):
        result = sample_result("test_passes", "test_fails", "test_skipped_a", "test_skipped_b")
        text = "\n".join(summary_format(is_ruff_ok=False, ruff_output="x.py:1:1: F401 unused", result=result, seconds=2))
        self.assertTrue(text.startswith("ruff FAILED · 1 passed · 1 FAILED · 2 skipped · 2.0 s"), text)
        self.assertIn("F401 unused", text)
        self.assertEqual(text.count("FAIL: tests.test_check.sample_result.<locals>.Sample.test_fails"), 1)
        self.assertIn("AssertionError: 1 != 2", text)
        self.assertIn("2 × needs a service", text)
        self.assertNotIn("test_passes", text)


if __name__ == "__main__":
    unittest.main()
