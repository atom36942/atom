"""Atom's Python files (routers, functions, scripts and sync.py) keep the section headers AGENTS.md describes, so every file reads the same way."""
import ast
import io
import re
import sys
import tokenize
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SECTIONS = ["import", "config", "setting", "logic", "main"]
MAIN_LINES_MAX = 30
SCRIPT_PATHS = [*sorted((ROOT / "script").glob("*.py")), ROOT / "sync.py"]


def tokens(path):
    return list(tokenize.generate_tokens(io.StringIO(path.read_text()).readline))


def headers(path):
    """{line number: name} of section headers ('# import' comments; text inside strings doesn't count)."""
    return {token.start[0]: match.group(1) for token in tokens(path) if token.type == tokenize.COMMENT and token.start[1] == 0 and (match := re.fullmatch(r"# ([a-z_]+)", token.string))}


def sections(path):
    """The file's section headers, in order."""
    return list(headers(path).values())


def section_lines(path, name):
    """(first, last) line numbers of a section's body."""
    found = headers(path)
    start = next(line for line, header in found.items() if header == name)
    following = [line for line in found if line > start]
    return start + 1, following[0] - 1 if following else len(path.read_text().splitlines())


def section_body(path, name):
    first, last = section_lines(path, name)
    return "\n".join(path.read_text().splitlines()[first - 1:last]) + "\n"


class FileStructureTests(unittest.TestCase):
    def test_routers_and_functions_have_their_headers(self):
        for folder, expected in (("router", ["import", "router", "api"]), ("function", ["import", "function"])):
            for path in sorted((ROOT / folder).glob("*.py")):
                if path.name == "__init__.py": continue
                with self.subTest(file=f"{folder}/{path.name}"): self.assertEqual(sections(path), expected)

    def test_scripts_have_every_section_in_order(self):
        for path in SCRIPT_PATHS:
            with self.subTest(script=path.name):
                lines = path.read_text().splitlines()
                self.assertRegex(lines[0], r"^# command: \S")
                self.assertTrue(any(re.match(r"^# info: \S", line) for line in lines[:4]), "# info: <one line> near the top")
                self.assertEqual(sections(path), SCRIPT_SECTIONS)

    def test_script_settings_are_upper_case_constants(self):
        for path in SCRIPT_PATHS:
            names = [target.id for node in ast.parse(section_body(path, "setting")).body if isinstance(node, ast.Assign) for target in node.targets if isinstance(target, ast.Name)]
            with self.subTest(script=path.name): self.assertEqual([name for name in names if not name.isupper()], [])

    def test_script_config_and_settings_are_compact(self):
        for path in SCRIPT_PATHS:
            for name in ("config", "setting"):
                first, last = section_lines(path, name)
                blank = [token.start[0] for token in tokens(path) if token.type == tokenize.NL and not token.line.strip() and first <= token.start[0] < last]    # blank lines inside strings make no NL token
                with self.subTest(script=path.name, section=name): self.assertEqual(blank, [])

    def test_script_main_only_starts_main(self):
        for path in SCRIPT_PATHS:
            body = ast.parse(section_body(path, "main")).body
            with self.subTest(script=path.name):
                self.assertEqual(len(body), 1)
                self.assertIn("__name__", ast.unparse(body[0].test))
                self.assertIn("main()", ast.unparse(body[0]))
                self.assertTrue(any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main" for node in ast.parse(path.read_text()).body), "a main() function in # logic")

    def test_scripts_import_only_packages_config_and_function(self):
        local = {path.stem for path in ROOT.iterdir() if path.suffix == ".py" or (path.is_dir() and not path.name.startswith("."))}
        for path in SCRIPT_PATHS:
            tree = ast.parse(path.read_text())
            modules = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names} | {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
            allowed = set() if path.name == "sync.py" else {"config", "function"}    # sync.py runs on the system Python before venv/ exists: stdlib only
            folders = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str) and re.match(r"(files|static|router|function|script|docs)(_extend)?/", node.value)]
            with self.subTest(script=path.name):
                self.assertEqual(sorted({module for module in modules if module in local or module.endswith("_extend")} - allowed), [], "Atom scripts import only packages, config and function")
                if path.name == "sync.py": self.assertEqual(sorted(modules - set(sys.stdlib_module_names)), [], "sync.py imports only the standard library")
                else: self.assertEqual(folders, [], "scripts write only to tmp/")

    def test_script_logic_is_small_helpers_then_main(self):
        for path in SCRIPT_PATHS:
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
