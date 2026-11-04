"""Atom's long pages mark their sections (/* ==== name ==== */), so one search lists where each part starts."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LONG_PAGE_LINES = 300
SECTION = re.compile(r"^\s*(/\* ==== .+ ==== \*/|<!-- ==== .+ ==== -->)$", re.MULTILINE)


class PageSectionTests(unittest.TestCase):
    def test_long_pages_mark_their_style_and_script_sections(self):
        for path in sorted((ROOT / "static").glob("*.html")):
            text = path.read_text()
            if text.count("\n") < LONG_PAGE_LINES: continue
            for tag in ("style", "script"):
                block = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL).group(1)
                with self.subTest(page=path.name, block=tag): self.assertGreaterEqual(len(SECTION.findall(block)), 2)

    def test_markers_use_one_format(self):
        for path in sorted((ROOT / "static").glob("*.html")):
            loose = [line.strip() for line in path.read_text().splitlines() if "====" in line and not SECTION.match(line)]
            with self.subTest(page=path.name): self.assertEqual(loose, [], "markers are /* ==== name ==== */ or <!-- ==== name ==== -->")


if __name__ == "__main__":
    unittest.main()
