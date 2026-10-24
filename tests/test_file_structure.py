"""Atom's Python files keep the section headers AGENTS.md describes, so every file reads the same way."""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SECTIONS = ["import", "config", "setting", "logic", "main"]
MAIN_LINES_MAX = 30


def sections(path):
    """The file's section headers (lines like '# import'), in order."""
    return re.findall(r"^# ([a-z_]+)$", path.read_text(), re.M)


def section_body(path, name):
    text = path.read_text()
    start = text.index(f"\n# {name}\n") + len(name) + 3
    following = re.search(r"^# [a-z_]+$", text[start:], re.M)
    return text[start:start + following.start()] if following else text[start:]


class FileStructureTests(unittest.TestCase):
    def test_routers_and_functions_have_their_headers(self):
        for folder, expected in (("router", ["import", "router", "api"]), ("function", ["import", "function"])):
            for path in sorted((ROOT / folder).glob("*.py")):
                if path.name == "__init__.py": continue
                with self.subTest(file=f"{folder}/{path.name}"): self.assertEqual(sections(path), expected)

    def test_scripts_have_every_section_in_order(self):
        for path in sorted((ROOT / "script").glob("*.py")):
            with self.subTest(script=path.name):
                lines = path.read_text().splitlines()
                self.assertRegex(lines[0], r"^# command: \S")
                self.assertTrue(any(re.match(r"^# info: \S", line) for line in lines[:4]), "# info: <one line> near the top")
                self.assertEqual(sections(path), SCRIPT_SECTIONS)

    def test_script_settings_are_upper_case_constants(self):
        for path in sorted((ROOT / "script").glob("*.py")):
            names = [target.id for node in ast.parse(section_body(path, "setting")).body if isinstance(node, ast.Assign) for target in node.targets if isinstance(target, ast.Name)]
            with self.subTest(script=path.name): self.assertEqual([name for name in names if not name.isupper()], [])

    def test_script_config_and_settings_are_compact(self):
        for path in sorted((ROOT / "script").glob("*.py")):
            for name in ("config", "setting"):
                with self.subTest(script=path.name, section=name): self.assertNotIn("\n\n", section_body(path, name).strip("\n"))

    def test_script_main_only_starts_main(self):
        for path in sorted((ROOT / "script").glob("*.py")):
            body = ast.parse(section_body(path, "main")).body
            with self.subTest(script=path.name):
                self.assertEqual(len(body), 1)
                self.assertIn("__name__", ast.unparse(body[0].test))
                self.assertIn("main()", ast.unparse(body[0]))
                self.assertTrue(any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main" for node in ast.parse(path.read_text()).body), "a main() function in # logic")

    def test_script_logic_is_small_helpers_then_main(self):
        for path in sorted((ROOT / "script").glob("*.py")):
            text = path.read_text()
            functions = [node for node in ast.parse(text).body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
            callbacks = set(re.findall(r"_callback=(\w+)", text))    # func_run_broker calls these positionally
            with self.subTest(script=path.name):
                self.assertEqual(functions[-1].name, "main", "main() is the last function")
                main = functions[-1]
                self.assertLessEqual(main.end_lineno - main.lineno + 1, MAIN_LINES_MAX, "main() reads like steps; move work into helpers")
                self.assertEqual([node.name for node in ast.walk(main) if node is not main and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))], [], "no functions defined inside main()")
                self.assertEqual([node.name for node in functions if node.args.args and node.name not in callbacks], [], "helpers take keyword-only arguments")


if __name__ == "__main__":
    unittest.main()
