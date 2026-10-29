"""static/pgweb.html is edited by hand-free tooling and has no browser test run, so check the wiring a typo would break."""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

PAGE = (Path(__file__).resolve().parents[1] / "static" / "pgweb.html").read_text()
SCRIPT = "\n".join(re.findall(r"<script>(.*?)</script>", PAGE, re.S))
DEFINED = set(re.findall(r'\bid="([\w-]+)"', PAGE)) | set(re.findall(r"\.id\s*=\s*'([\w-]+)'", PAGE)) | set(re.findall(r'id=\\"([\w-]+)\\"', PAGE))


class PgwebPageTests(unittest.TestCase):
    def test_every_element_the_script_looks_up_exists(self):
        used = set(re.findall(r"\$\('([\w-]+)'\)", SCRIPT))
        self.assertEqual(sorted(used - DEFINED), [])

    def test_element_ids_are_unique(self):
        # the fixed markup only: dialogs reuse ids like dyes in innerHTML, one dialog at a time
        ids = re.findall(r'\bid="([\w-]+)"', re.sub(r"<script>.*?</script>", "", PAGE, flags=re.S))
        self.assertEqual(sorted({i for i in ids if ids.count(i) > 1}), [])

    def test_main_controls_are_present(self):
        for element in ("home-dsn", "tree", "sidetabs", "vp", "rows", "rowpanel", "rp-body", "sql", "run", "resetsql", "pagesize", "pagenav", "fslow", "connbtn", "dlg", "moremenu"):
            with self.subTest(element=element): self.assertIn(element, DEFINED)

    @unittest.skipUnless(shutil.which("node"), "node is not installed (CI runners have it)")
    def test_script_parses(self):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as script: script.write(SCRIPT)
        result = subprocess.run(["node", "--check", script.name], capture_output=True, text=True)  # noqa: S603, S607 - fixed command, our own file
        Path(script.name).unlink()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_api_actions_the_page_calls_exist_on_the_server(self):
        server = (Path(__file__).resolve().parents[1] / "function" / "pgweb.py").read_text()
        called = set(re.findall(r"action:\s*'([a-z_]+)'", SCRIPT))
        known = set(re.findall(r'"([a-z_]+)": app_state\.func_pgweb_', server)) | set(re.findall(r'action == "([a-z_]+)"', server)) | set(re.findall(r'"action"\) == "([a-z_]+)"', server))
        self.assertEqual(sorted(called - known), [])


if __name__ == "__main__":
    unittest.main()
