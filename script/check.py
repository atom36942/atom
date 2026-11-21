# type: job

# command: venv/bin/python -m script.check
# command: venv/bin/python -m script.check tests.test_sync    (one module, class or test; ruff still runs)

# info: Runs Atom's startup checks, ruff, a syntax check of the pages' JavaScript and the tests in one go and prints only what needs attention: a summary line, each failing test with its traceback, and why tests were skipped.
# - startup: imports the app and runs func_check in a separate process, with the project's .env: catches config, duplicate func_* and import errors without opening a connection or starting a server
# - names: every app_state.func_* the project's code calls (function_extend, router_extend, script_extend, files_extend, config_extend.py) is defined in Atom or the project; a name Atom renamed or removed otherwise fails only when that line runs
# - routes (projects only): every quoted path in static_extend/ pages and .js files whose first part is a config_api route's first part (/admin, /my, /auth, the project's own /<feature>, ...) is a config_api route; ${...} counts as one route value ({name}), anything after ? or # is ignored, and /static/ files and third-party URLs are not checked; a route Atom renamed or removed otherwise fails only when the page calls it
# - pages: every .html (its inline scripts) and .js file in static/ and static_extend/ is parsed with node --check; skipped when node is not installed
# - tests come from tests/ in Atom and tests_extend/ in a project; service tests run when their ATOM_TEST_* setting is in the environment (see tests/README.md)
# - rules (projects only): AGENTS.md's Enforced code rules: no secret in code or docs, Postgres only through asyncpg, .env in .gitignore, no pool or SDK client opened in function_extend/ or router_extend/, no role or permission check in router_extend/; each break is named with its file and line
# - standard (projects only, report only, never fails the check): how many of AGENTS.md's measurable Defaults the project's code and pages follow, and which it misses; a Default kept on purpose has its reason in docs_extend/
# - a test running over TEST_TIMEOUT_SEC stops the check: it prints the test and every thread's stack (where it waits), then exits 1
# - exit code 0 only when startup, ruff, names, routes, rules, pages and every test pass

# import
import ast
import faulthandler
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import unittest
from collections import Counter
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

# config

# setting
TEST_FOLDERS = ["tests", "tests_extend"]
SKIP_REASONS_MAX = 5
STARTUP_CODE = "import main; main.app.state.func_check(app=main.app)"
STARTUP_TIMEOUT_SEC = 120
STARTUP_ERROR_LINES = 3
TEST_TIMEOUT_SEC = 60
PAGE_FOLDERS = ["static", "static_extend"]
NAME_DEFINE_FOLDERS = ["function", "router", "script", "function_extend", "router_extend", "script_extend", "files_extend"]
NAME_USE_FOLDERS = ["function_extend", "router_extend", "script_extend", "files_extend"]
NAME_DEFINE = re.compile(r"^\s*(?:async\s+)?def\s+(func_\w+)", re.MULTILINE)
NAME_USE = re.compile(r"\bstate\.(func_\w+)")
ROUTE_PAGE_FOLDER = "static_extend"
ROUTE_SKIP = {"", "static"}    # "/" and the /static file mount: not API routes
ROUTE_START = re.compile(r"""(["'`])/(?=[A-Za-z$])""")
PAGE_TMP = "tmp/check"
SCRIPT_TAG = re.compile(r"<script(?P<attrs>[^>]*)>(?P<code>.*?)</script>", re.DOTALL | re.IGNORECASE)
SCRIPT_TYPES = ("", "text/javascript", "module")    # other types (application/json, importmap, templates) are not JavaScript
SECRET_PATTERNS = [r"AKIA[0-9A-Z]{16}", r"sk-[A-Za-z0-9_-]{20,}", r"-----BEGIN [A-Z ]*PRIVATE KEY", r"(postgres(ql)?|redis|mongodb(\+srv)?|amqp)://[^:/\s\"']+:[^@\s\"']+@"]
STANDARD_PAGE_LOGIN = "/auth/login"
RULE_CODE_FOLDERS = ["function_extend", "router_extend", "script_extend", "files_extend", "static_extend", "docs_extend"]
RULE_CLIENT_FOLDERS = ["function_extend", "router_extend"]    # scripts run as their own process and may open their own
RULE_CLIENT_CALLS = {"asyncpg.create_pool", "asyncpg.connect", "create_pool", "redis.Redis", "Redis", "redis.from_url", "Redis.from_url", "httpx.AsyncClient", "httpx.Client", "AsyncClient", "boto3.client", "boto3.resource", "AsyncIOMotorClient", "MongoClient", "OpenAI", "AsyncOpenAI", "openai.OpenAI", "openai.AsyncOpenAI", "Anthropic", "AsyncAnthropic", "anthropic.Anthropic", "anthropic.AsyncAnthropic", "genai.Client", "BlobServiceClient", "BlobServiceClient.from_connection_string"}
RULE_ACCESS_FOLDER = "router_extend"
RULE_ACCESS_KEYS = {"role", "permissions"}
RULE_DRIVERS = re.compile(r"^\s*(import|from)\s+(psycopg|psycopg2|sqlalchemy)\b", re.MULTILINE)
STANDARD_PAGE_DEFAULTS = [
    ("keeps the login alive (/my/token-refresh)", ["/my/token-refresh"]),
    ("loads /my/profile after login", ["/my/profile"]),
    ("Sync reads /info", ["/info"]),
    ("export up to /info export_limit", ["export_limit"]),
]

# logic
def startup_begin():
    """Start the startup check in its own process (the app's .env stays out of the tests); Sentry is off so a failed check is not reported."""
    env = {**os.environ.copy(), "config_sentry_dsn": ""}
    return subprocess.Popen([sys.executable, "-c", STARTUP_CODE], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)    # noqa: S603 - fixed command, no user input


def startup_finish(*, process):
    """(is_ok, output) of the startup check: on a failure, the last lines of its error."""
    try: _, error = process.communicate(timeout=STARTUP_TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        process.kill()
        return False, f"no answer in {STARTUP_TIMEOUT_SEC} s: something waits at import (a network call outside func_extend?)"
    lines = [line for line in error.splitlines() if line.strip()]
    return process.returncode == 0, "\n".join(lines[-STARTUP_ERROR_LINES:])


def page_scripts_read(*, path):
    """[(is_module, code)] to check: an .html file's inline scripts, padded with blank lines so node's line numbers match the page, or a .js file itself."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".js": return [(None, text)]    # None: classic or module, whichever parses
    scripts = []
    for match in SCRIPT_TAG.finditer(text):
        attrs = match.group("attrs").lower()
        kind = (re.search(r"""type\s*=\s*["']?([^"'\s>]+)""", attrs) or [None, ""])[1]
        if "src=" in attrs or kind not in SCRIPT_TYPES: continue
        scripts.append((kind == "module", "\n" * text.count("\n", 0, match.start("code")) + match.group("code")))
    return scripts


def node_check(*, node, code, is_module, name):
    """node --check on code saved under tmp/; the error with the temporary path replaced by name, or None when it parses."""
    error = None
    for suffix in ([".mjs"] if is_module else [".cjs"] if is_module is False else [".cjs", ".mjs"]):
        file = Path(PAGE_TMP, f"page{suffix}")
        file.write_text(code, encoding="utf-8")
        done = subprocess.run([node, "--check", str(file)], capture_output=True, text=True)    # noqa: S603 - node from PATH, a file this script wrote
        if done.returncode == 0: return None
        error = error or done.stderr.replace(str(file.resolve()), name).replace(str(file), name).strip()
    return error


def pages_check():
    """(status, output) of the JavaScript syntax check: True ok, False with the errors, None skipped with the reason."""
    node = shutil.which("node")
    if not node: return None, "node is not installed: page scripts were not checked"
    paths = sorted(path for folder in PAGE_FOLDERS if Path(folder).is_dir() for path in Path(folder).rglob("*") if path.suffix in (".html", ".js") and path.is_file())
    os.makedirs(PAGE_TMP, exist_ok=True)
    try: errors = [error for path in paths for is_module, code in page_scripts_read(path=path) if (error := node_check(node=node, code=code, is_module=is_module, name=str(path)))]
    finally: shutil.rmtree(PAGE_TMP, ignore_errors=True)
    return not errors, "\n\n".join(errors)


def names_check(*, root="."):
    """(status, output) of the project's app_state.func_* calls: True ok, False with each unknown name and where it is used, None outside a project."""
    if not Path(root, "config_extend.py").is_file(): return None, "not a project (no config_extend.py)"
    def files(folders): return [path for folder in folders for path in Path(root, folder).rglob("*.py")]
    defined = {name for path in [*files(NAME_DEFINE_FOLDERS), Path(root, "main.py")] if path.is_file() for name in NAME_DEFINE.findall(path.read_text(encoding="utf-8", errors="replace"))}
    unknown = [f"{path.relative_to(root)}:{number}: {name} is not defined in Atom or the project (renamed or removed? see CHANGELOG.md)" for path in [*files(NAME_USE_FOLDERS), Path(root, "config_extend.py")] for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1) for name in NAME_USE.findall(line) if name not in defined]
    return not unknown, "\n".join(unknown)


def route_paths(*, text):
    """[(line, path)] for every quoted string in text that starts with /<letter>: the path up to its quote, whitespace, ? or #, with each ${...} of a template as {}."""
    paths = []
    for match in ROUTE_START.finditer(text):
        quote, index, path = match.group(1), match.end() - 1, ""
        while index < len(text):
            if quote == "`" and text.startswith("${", index):
                depth, index = 1, index + 2
                while index < len(text) and depth:
                    depth += {"{": 1, "}": -1}.get(text[index], 0)
                    index += 1
                path += "{}"
                continue
            if text[index] in "\"'`?#" or text[index].isspace(): break
            path += text[index]
            index += 1
        paths.append((text.count("\n", 0, match.start()) + 1, path))
    return paths


def routes_config_api():
    """The project's config_api: config_extend.py's when it defines one (it keeps Atom's entries), else Atom's config.py."""
    import importlib
    return getattr(importlib.import_module("config_extend"), "config_api", None) or importlib.import_module("config").config_api


def routes_check(*, root=".", config_api=None):
    """(status, output) of the routes the project's pages call: True ok, False with each unknown path and where it is, None outside a project."""
    if not Path(root, "config_extend.py").is_file(): return None, "not a project (no config_extend.py)"
    routes = config_api if config_api is not None else routes_config_api()
    patterns = [re.compile("^" + re.sub(r"\\\{[^/]*?\\\}", "[^/]+", re.escape(route)) + "$") for route in routes]
    starts = {route.strip("/").split("/")[0] for route in routes} - ROUTE_SKIP
    def is_route(path): return any(pattern.match(path) for pattern in patterns) or (path.endswith("{}") and not path.endswith("/{}") and is_route(path[:-2]))    # a trailing ${...} glued to the route adds its query
    paths = sorted(path for path in Path(root, ROUTE_PAGE_FOLDER).rglob("*") if path.suffix in (".html", ".js") and path.is_file())
    unknown = [f"{page.relative_to(root)}:{line}: {path} is not a route in config_api (renamed or removed? see CHANGELOG.md)" for page in paths for line, path in route_paths(text=page.read_text(encoding="utf-8", errors="replace")) if path.strip("/").split("/")[0] in starts and not is_route(path)]
    return not unknown, "\n".join(unknown)


def ruff_run():
    """(is_ok, output) of ruff on the whole project; ruff comes from the venv running this script."""
    ruff = Path(sys.executable).parent / ("ruff.exe" if os.name == "nt" else "ruff")
    if not ruff.exists(): return False, f"ruff not found at {ruff}: run python3 sync.py to rebuild venv/"
    done = subprocess.run([str(ruff), "check", ".", "--output-format", "concise", "--quiet"], capture_output=True, text=True)    # noqa: S603 - fixed command, no user input
    return done.returncode == 0, (done.stdout + done.stderr).strip()


def standard_pages(*, root):
    """{page name: its text (an .html page, or a folder page's .html, .js and .css files)} for static_extend/."""
    folder = Path(root, "static_extend")
    if not folder.is_dir(): return {}
    pages = {path.stem: path.read_text(encoding="utf-8", errors="replace") for path in folder.glob("*.html")}
    for index in folder.glob("*/index.html"): pages[index.parent.name] = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in sorted(index.parent.rglob("*")) if path.suffix in (".html", ".js", ".css") and path.is_file())
    return pages


def rule_call_name(*, node):
    """The dotted name a call is made on (redis.asyncio.Redis.from_url → redis.asyncio.Redis.from_url), or "" for anything else."""
    parts, node = [], node.func
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name): parts.append(node.id)
    return ".".join(reversed(parts))


def rule_client_opened(*, tree):
    """[(line, call)] for every pool or SDK client the code opens itself."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call): continue
        name = rule_call_name(node=node)
        if any(name == call or name.endswith("." + call) for call in RULE_CLIENT_CALLS): found.append((node.lineno, name))
    return found


def rule_access_checked(*, tree):
    """[(line, key)] for every role or permissions read from the request's user (request.state.user["role"], .get("permissions"))."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value in RULE_ACCESS_KEYS and "state.user" in ast.unparse(node.value): found.append((node.lineno, node.slice.value))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value in RULE_ACCESS_KEYS and "state.user" in ast.unparse(node.func.value): found.append((node.lineno, node.args[0].value))
    return found


def rules_check(*, root="."):
    """(status, output) of AGENTS.md's Enforced code rules: True ok, False with each break and where it is, None outside a project."""
    root = Path(root)
    if not (root / "config_extend.py").is_file(): return None, "not a project (no config_extend.py)"
    files = [root / "config_extend.py", *sorted(path for folder in RULE_CODE_FOLDERS if (root / folder).is_dir() for path in (root / folder).rglob("*") if path.is_file() and path.suffix in (".py", ".html", ".js", ".css", ".md", ".json", ".sql", ".txt"))]
    secret = re.compile("|".join(SECRET_PATTERNS))
    breaks = []
    for path in files:
        name, text = str(path.relative_to(root)), path.read_text(encoding="utf-8", errors="replace")
        breaks += [f"{name}:{text.count(chr(10), 0, match.start()) + 1}: a secret in code (keep it in .env)" for match in secret.finditer(text)]
        if path.suffix != ".py": continue
        breaks += [f"{name}:{text.count(chr(10), 0, match.start()) + 1}: Postgres only through asyncpg (no {match.group(2)})" for match in RULE_DRIVERS.finditer(text)]
        try: tree = ast.parse(text)
        except SyntaxError: continue    # ruff and startup report it
        folder = path.relative_to(root).parts[0]
        if folder in RULE_CLIENT_FOLDERS: breaks += [f"{name}:{line}: {call}() opens a pool or client (use Atom's: app_state.client_*)" for line, call in rule_client_opened(tree=tree)]
        if folder == RULE_ACCESS_FOLDER: breaks += [f"{name}:{line}: checks the user's {key} in a route (config_api does it: user_check_role, user_check_permission)" for line, key in rule_access_checked(tree=tree)]
    gitignore = (root / ".gitignore").read_text(encoding="utf-8") if (root / ".gitignore").exists() else ""
    if not re.search(r"^/?\.env$", gitignore, re.MULTILINE): breaks.append(".gitignore: .env is not listed (it would be committed)")
    return not breaks, "\n".join(breaks)


def standard_check(*, root="."):
    """[(what, [what is missing])] of AGENTS.md's measurable Defaults for a project, empty when there is no project code yet; None outside a project (no config_extend.py)."""
    root = Path(root)
    if not (root / "config_extend.py").exists(): return None
    features = sorted(path.stem for path in (root / "router_extend").glob("*.py") if path.stem != "__init__") if (root / "router_extend").is_dir() else []
    pages = standard_pages(root=root)
    defaults = [
        ("each route file has its function_extend/<f>.py", [f for f in features if not (root / "function_extend" / f"{f}.py").exists()]),
        ("each feature has docs_extend/<f>.md", [f for f in features if not (root / "docs_extend" / f"{f}.md").exists()]),
        ("each feature has tests_extend/test_<f>.py", [f for f in features if not (root / "tests_extend" / f"test_{f}.py").exists()]),
        ("pages load no script or style from another site", [name for name, text in pages.items() if re.search(r"<(script|link)[^>]+(src|href)=[\"']?(https?:)?//", text, re.IGNORECASE)]),
        ("pages fit a phone (viewport meta)", [name for name, text in pages.items() if 'name="viewport"' not in text]),
    ]
    logins = {name: text for name, text in pages.items() if STANDARD_PAGE_LOGIN in text}
    return defaults + [(what, [name for name, text in logins.items() if not all(word in text for word in words)]) for what, words in STANDARD_PAGE_DEFAULTS]


def standard_format(*, standard):
    """(the summary part, the lines listing what is missing) of standard_check's result."""
    if standard is None: return None, []
    lines = [f"  {what}: {', '.join(missing)}" for what, missing in standard if missing]
    return f"standard Defaults {sum(not missing for _, missing in standard)}/{len(standard)}", (["", "standard (report only; a Default kept on purpose has its reason in docs_extend/):", *lines] if lines else [])


def tests_load(*, names):
    """A suite of the named tests, or of every test folder present."""
    loader = unittest.TestLoader()
    if names: return loader.loadTestsFromNames(names)
    suite = unittest.TestSuite()
    for folder in TEST_FOLDERS:
        if Path(folder, "__init__.py").exists(): suite.addTests(loader.discover(folder, top_level_dir="."))
    return suite


class WatchedResult(unittest.TextTestResult):
    """A unittest result that times each test: past timeout_sec it reports the test and where every thread waits, then ends the process (a hung test never returns)."""
    timeout_sec = TEST_TIMEOUT_SEC

    def startTest(self, test):
        self.timer = threading.Timer(self.timeout_sec, test_hung_report, kwargs={"test_id": test.id(), "timeout_sec": self.timeout_sec})
        self.timer.daemon = True
        self.timer.start()
        super().startTest(test)

    def stopTest(self, test):
        self.timer.cancel()
        super().stopTest(test)


def test_hung_report(*, test_id, timeout_sec):
    """Print the hung test and every thread's stack to the real stderr (the run's output is captured), then exit 1."""
    sys.__stderr__.write(f"HUNG: {test_id} (over {timeout_sec} s)\n")
    faulthandler.dump_traceback(file=sys.__stderr__, all_threads=True)
    sys.__stderr__.flush()
    os._exit(1)


def tests_run(*, suite, timeout_sec=TEST_TIMEOUT_SEC):
    """The unittest result; progress dots and test prints stay out of the output (a failing test's prints come back inside its traceback)."""
    result_class = type("Result", (WatchedResult,), {"timeout_sec": timeout_sec})
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()): return unittest.TextTestRunner(stream=StringIO(), verbosity=0, buffer=True, resultclass=result_class).run(suite)


def summary_format(*, steps, result, seconds, standard=None):
    """The lines to print: one summary line, then failed steps' output (startup, ruff, pages), failing tests, skip reasons and what the project misses of the standard. steps: [(name, status, output)], status True ok, False failed, None skipped (output: why)."""
    failed = len(result.failures) + len(result.errors) + len(result.unexpectedSuccesses)
    passed = result.testsRun - failed - len(result.skipped) - len(result.expectedFailures)
    parts = [*[f"{name} {'ok' if status else 'skipped' if status is None else 'FAILED'}" for name, status, _ in steps], f"{passed} passed"]
    if failed: parts.append(f"{failed} FAILED")
    if result.skipped: parts.append(f"{len(result.skipped)} skipped")
    standard_part, standard_lines = standard_format(standard=standard)
    lines = [" · ".join([*parts, *([standard_part] if standard_part else []), f"{seconds:.1f} s"])]
    for name, status, output in steps:
        if status is False: lines += ["", f"{name}:", output]
    for kind, items in (("FAIL", result.failures), ("ERROR", result.errors)):
        for test, trace in items: lines += ["", f"{kind}: {test.id()}", trace.rstrip()]
    for test in result.unexpectedSuccesses: lines += ["", f"UNEXPECTED SUCCESS: {test.id()}"]
    reasons = Counter([*[reason for _, reason in result.skipped], *[f"{name}: {output}" for name, status, output in steps if status is None]])
    if reasons: lines += ["", "skipped:", *[f"  {count} × {reason}" for reason, count in reasons.most_common(SKIP_REASONS_MAX)]]
    return lines + standard_lines


def main():
    names = sys.argv[1:]    # optional test names, as unittest takes them
    started = time.monotonic()
    startup = startup_begin()    # runs while ruff and the tests do
    is_ruff_ok, ruff_output = ruff_run()
    pages = pages_check()
    result = tests_run(suite=tests_load(names=names))
    steps = [("startup", *startup_finish(process=startup)), ("ruff", is_ruff_ok, ruff_output), *([("names", *names)] if (names := names_check())[0] is not None else []), *([("routes", *routes)] if (routes := routes_check())[0] is not None else []), *([("rules", *rules)] if (rules := rules_check())[0] is not None else []), ("pages", *pages)]
    print("\n".join(summary_format(steps=steps, result=result, seconds=time.monotonic() - started, standard=standard_check())))
    sys.exit(0 if all(status is not False for _, status, _ in steps) and result.wasSuccessful() else 1)

# main
if __name__ == "__main__":
    main()
