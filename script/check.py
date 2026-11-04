# command: venv/bin/python -m script.check
# command: venv/bin/python -m script.check tests.test_sync    (one module, class or test; ruff still runs)

# info: Runs Atom's startup checks, ruff and the tests in one go and prints only what needs attention: a summary line, each failing test with its traceback, and why tests were skipped.
# - startup: imports the app and runs func_check in a separate process, with the project's .env: catches config, duplicate func_* and import errors without opening a connection or starting a server
# - tests come from tests/ in Atom and tests_extend/ in a project; service tests run when their ATOM_TEST_* setting is in the environment or .env (see tests/README.md)
# - exit code 0 only when startup, ruff and every test pass

# import
import os
import subprocess
import sys
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


def ruff_run():
    """(is_ok, output) of ruff on the whole project; ruff comes from the venv running this script."""
    ruff = Path(sys.executable).parent / ("ruff.exe" if os.name == "nt" else "ruff")
    if not ruff.exists(): return False, f"ruff not found at {ruff}: run python3 sync.py to rebuild venv/"
    done = subprocess.run([str(ruff), "check", ".", "--output-format", "concise", "--quiet"], capture_output=True, text=True)    # noqa: S603 - fixed command, no user input
    return done.returncode == 0, (done.stdout + done.stderr).strip()


def tests_load(*, names):
    """A suite of the named tests, or of every test folder present."""
    loader = unittest.TestLoader()
    if names: return loader.loadTestsFromNames(names)
    suite = unittest.TestSuite()
    for folder in TEST_FOLDERS:
        if Path(folder, "__init__.py").exists(): suite.addTests(loader.discover(folder, top_level_dir="."))
    return suite


def tests_run(*, suite):
    """The unittest result; progress dots and test prints stay out of the output (a failing test's prints come back inside its traceback)."""
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()): return unittest.TextTestRunner(stream=StringIO(), verbosity=0, buffer=True).run(suite)


def summary_format(*, steps, result, seconds):
    """The lines to print: one summary line, then failed steps' output (startup, ruff), failing tests and skip reasons. steps: [(name, is_ok, output)]."""
    failed = len(result.failures) + len(result.errors) + len(result.unexpectedSuccesses)
    passed = result.testsRun - failed - len(result.skipped) - len(result.expectedFailures)
    parts = [*[f"{name} ok" if is_ok else f"{name} FAILED" for name, is_ok, _ in steps], f"{passed} passed"]
    if failed: parts.append(f"{failed} FAILED")
    if result.skipped: parts.append(f"{len(result.skipped)} skipped")
    lines = [" · ".join([*parts, f"{seconds:.1f} s"])]
    for name, is_ok, output in steps:
        if not is_ok: lines += ["", f"{name}:", output]
    for kind, items in (("FAIL", result.failures), ("ERROR", result.errors)):
        for test, trace in items: lines += ["", f"{kind}: {test.id()}", trace.rstrip()]
    for test in result.unexpectedSuccesses: lines += ["", f"UNEXPECTED SUCCESS: {test.id()}"]
    reasons = Counter(reason for _, reason in result.skipped)
    if reasons: lines += ["", "skipped:", *[f"  {count} × {reason}" for reason, count in reasons.most_common(SKIP_REASONS_MAX)]]
    return lines


def main():
    names = sys.argv[1:]    # optional test names, as unittest takes them
    started = time.monotonic()
    startup = startup_begin()    # runs while ruff and the tests do
    is_ruff_ok, ruff_output = ruff_run()
    result = tests_run(suite=tests_load(names=names))
    steps = [("startup", *startup_finish(process=startup)), ("ruff", is_ruff_ok, ruff_output)]
    print("\n".join(summary_format(steps=steps, result=result, seconds=time.monotonic() - started)))
    sys.exit(0 if all(is_ok for _, is_ok, _ in steps) and result.wasSuccessful() else 1)

# main
if __name__ == "__main__":
    main()
