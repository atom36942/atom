"""
Atom Test Reporter — Custom pytest plugin.

Registered via conftest.py pytest_configure hook.
Replaces default terminal output with a clean, minimal table.
"""
import sys
import time
import pytest
from _pytest.terminal import TerminalReporter

class AtomReporter(TerminalReporter):
    def __init__(self, config, file=None):
        super().__init__(config, file)
        self._idx = 0
        self._module = ""
        self._passed = 0
        self._failed = 0
        self._skipped = 0
        self._errors = []
        self._start = time.time()

    # ── Suppress all default output ──────────────────────────────────
    def report_collect(self, final=False):
        pass  # Suppress default collection output

    def pytest_sessionstart(self, session):
        self._session = session
        self._start = time.time()

    def pytest_runtest_logreport(self, report):
        if report.when != "call" and not (report.when == "setup" and report.skipped):
            return
        self._idx += 1
        parts = report.nodeid.split("::")
        module = parts[0].replace("tests/test_", "").replace(".py", "")
        name = parts[1] if len(parts) > 1 else "?"
        if module != self._module:
            self._module = module
            self._write(f"\n  {'─' * 70}\n  📦 {module}\n  {'─' * 70}\n")
        if report.passed:
            icon, remark = "✅", ""
            self._passed += 1
        elif report.skipped:
            icon = "⏭️ "
            self._skipped += 1
            reason = ""
            if hasattr(report, "longrepr") and report.longrepr:
                reason = str(report.longrepr[-1]) if isinstance(report.longrepr, tuple) else str(report.longrepr)
                reason = reason.split("Skipped: ")[-1][:30] if "Skipped" in reason else reason[:30]
            remark = reason
        else:
            icon = "❌"
            self._failed += 1
            msg = str(report.longrepr).split("\n")[-1][:50] if report.longrepr else ""
            remark = msg
            self._errors.append(f"  {report.nodeid}: {msg}")
        self._write(f"  {self._idx:>4}  {icon}  {name:<55} {remark}\n")

    def summary_stats(self):
        elapsed = round(time.time() - self._start, 2)
        total = self._passed + self._failed + self._skipped
        health = round(self._passed / (self._passed + self._failed) * 100, 1) if (self._passed + self._failed) > 0 else 100
        bar_len = 40
        filled = int(bar_len * health / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        out = f"""
  {'═' * 70}
  📊 Test Summary                              ⏱️  {elapsed}s
  {'═' * 70}
    Total    : {total}
    ✅ Passed : {self._passed}
    ❌ Failed : {self._failed}
    ⏭️  Skipped: {self._skipped}
"""
        if self._errors:
            out += "\n  🔴 Failures:\n"
            for e in self._errors:
                out += e + "\n"
        out += f"\n  Health: [{bar}] {health}%\n  {'═' * 70}\n"
        self._write(out)

    # ── Suppress default summary sections ────────────────────────────
    def summary_failures(self): pass
    def summary_errors(self): pass
    def summary_warnings(self): pass
    def summary_passes(self): pass
    def short_test_summary(self): pass
    def summary_deselected(self): pass

    def _write(self, text):
        sys.stdout.write(text)
        sys.stdout.flush()
