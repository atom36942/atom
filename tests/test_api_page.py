"""static/api.html (the API console at /) is edited by tooling and has no browser test run, so check the wiring a typo would break."""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

PAGE = (Path(__file__).resolve().parents[1] / "static" / "api.html").read_text()
SCRIPT = "\n".join(re.findall(r"<script>(.*?)</script>", PAGE, re.S))
MARKUP = re.sub(r"<script>.*?</script>", "", PAGE, flags=re.S)
DEFINED = set(re.findall(r'\bid="([\w-]+)"', PAGE)) | set(re.findall(r'\.id = "([\w-]+)"', SCRIPT))
BUTTONS = re.findall(r"<button\b[^>]*>.*?</button>", MARKUP, re.S)


class ApiPageTests(unittest.TestCase):
    def test_every_element_the_script_looks_up_exists(self):
        self.assertEqual(sorted(set(re.findall(r'UI\("([\w-]+)"\)', SCRIPT)) - DEFINED), [])

    def test_element_ids_are_unique(self):
        ids = re.findall(r'\bid="([\w-]+)"', MARKUP)
        self.assertEqual(sorted({i for i in ids if ids.count(i) > 1}), [])

    def test_every_icon_named_in_markup_exists(self):
        icons = set(re.findall(r"^  (\w+): s => SVG", SCRIPT, re.M))
        self.assertEqual(sorted(set(re.findall(r'data-icon="(\w+)"', MARKUP)) - icons), [])

    def test_every_icon_only_button_has_a_tooltip(self):
        # buttons with a visible word explain themselves; an icon or a single symbol (×, +) needs data-tip for the hover label
        missing = [re.search(r'id="([\w-]+)"', b).group(1) for b in BUTTONS if len(re.sub(r"<[^>]+>|\s", "", b)) <= 1 and "data-tip=" not in b]
        self.assertEqual(missing, [])

    def test_no_inline_handlers_or_styles_in_markup(self):
        self.assertNotRegex(MARKUP, r"\son[a-z]+=")
        self.assertNotRegex(MARKUP, r'\sstyle="')

    def test_main_controls_are_present(self):
        for element in ("apiInfoSearch", "apiInfoTbl", "apiRunnerModal", "apiForm", "subBtn", "rBox", "wsRunnerModal", "apiDetailModal", "infoModal", "pasteCurlModal", "paramInfoModal", "loginIndicator"):
            with self.subTest(element=element): self.assertIn(element, DEFINED)

    @unittest.skipUnless(shutil.which("node"), "node is not installed (CI runners have it)")
    def test_script_parses(self):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as script: script.write(SCRIPT)
        result = subprocess.run(["node", "--check", script.name], capture_output=True, text=True)  # noqa: S603, S607 - fixed command, our own file
        Path(script.name).unlink()
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
