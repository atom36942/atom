"""static/home.html (the page at /) lists Atom's and the project's HTML apps from /static-pages."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "static" / "home.html").read_text()


class HomePageTests(unittest.TestCase):
    def test_home_is_the_default_root_page(self):
        self.assertIn('config_root_html_path = "static/home.html"', (ROOT / "config.py").read_text())

    def test_the_route_the_page_calls_exists_and_is_public(self):
        self.assertIn('fetch("/static-pages")', PAGE)
        self.assertIn('@router.get("/static-pages")', (ROOT / "router" / "index.py").read_text())
        self.assertRegex((ROOT / "config.py").read_text(), r'"/static-pages": \{"id": \d+, "is_token": False')

    def test_every_element_the_script_looks_up_exists(self):
        used = set(re.findall(r'getElementById\("([\w-]+)"\)', PAGE))
        self.assertEqual(sorted(used - set(re.findall(r'\bid="([\w-]+)"', PAGE))), [])

    def test_page_text_is_escaped(self):
        # titles come from files on disk; they go into innerHTML only through he()
        cards = next(line for line in PAGE.splitlines() if "appsEl.innerHTML" in line)
        self.assertNotRegex(cards, r"\$\{p\.(title|url|name)\}")


if __name__ == "__main__":
    unittest.main()
