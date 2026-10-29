"""The monitor page stands alone: its own login and storage, so it works without any other page."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "static" / "monitor.html").read_text()
CONFIG = (ROOT / "config.py").read_text()


class MonitorPageTests(unittest.TestCase):
    def test_every_element_the_script_looks_up_exists(self):
        used = set(re.findall(r'\$\("([\w-]+)"\)', PAGE))
        self.assertEqual(sorted(used - set(re.findall(r'\bid="([\w-]+)"', PAGE))), [])

    def test_page_keeps_its_own_login_and_storage(self):
        self.assertIn('const STORAGE_KEY = "monitor";', PAGE)
        self.assertEqual(set(re.findall(r'localStorage\.\w+\(([^,)]+)', PAGE)), {"STORAGE_KEY"})
        self.assertIn('fetch("/auth/login-username-password"', PAGE)

    def test_the_route_the_page_calls_exists_and_is_admin_only(self):
        self.assertIn("api(`/admin/monitor?", PAGE)
        self.assertIn('@router.get("/admin/monitor")', (ROOT / "router" / "admin.py").read_text())
        self.assertRegex(CONFIG, r'"/admin/monitor": \{"id": \d+, "is_token": True, "user_check_role": \{"mode": "token", "roles": \[1\]\}')

    def test_every_tab_has_a_view_the_route_allows(self):
        tabs = re.findall(r'data-tab="(\w+)"', PAGE)
        allowed = re.search(r'"name": "view", "type": "str", "allowed": \[([^\]]+)\]', (ROOT / "router" / "admin.py").read_text()).group(1)
        self.assertEqual(tabs, re.findall(r'"(\w+)"', allowed))

    def test_report_text_is_escaped(self):
        # names come from the server; every interpolated name or file goes through he()
        self.assertNotRegex(PAGE, r"\$\{(item|o|c|t)\.(name|type|file)\}")


if __name__ == "__main__":
    unittest.main()
