"""static/atom.html (/page/atom): the public page about Atom, for anyone, with no login."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "static" / "atom.html").read_text()
THEME = re.compile(r"<!-- ==== atom page: theme ==== -->.*?<!-- ==== end atom page: theme ==== -->", re.S)


class AtomPageTests(unittest.TestCase):
    def test_theme_block_is_atom_s_own(self):
        self.assertEqual(THEME.search(PAGE).group(0), THEME.search((ROOT / "static" / "home.html").read_text()).group(0))
        self.assertIn('data-storage-key="atom"', PAGE)

    def test_needs_no_login_and_no_outside_server(self):
        self.assertNotIn("Authorization", PAGE)
        self.assertNotIn("localStorage.setItem", PAGE.split("<!-- ==== end atom page: theme ==== -->")[1])
        self.assertIsNone(re.search(r"<(script|link)[^>]+(src|href)=\"https?://", PAGE), "no script or style from another site")

    def test_calls_no_route(self):
        self.assertNotIn("fetch(", PAGE, "a display page: it shows the same to everyone, whatever the server")

    def test_links_to_the_public_repository(self):
        self.assertIn('href="https://github.com/atom36942/atom"', PAGE)


if __name__ == "__main__":
    unittest.main()
