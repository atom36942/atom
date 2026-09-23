"""Updater integration tests use disposable local Git repositories only."""

from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import sync


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.upstream = self.base / "upstream"
        self.upstream.mkdir()
        self.git(self.upstream, "init", "-b", "main")
        for name in sync.files_to_sync:
            if name in ("function", "docs"):
                continue
            self.write(self.upstream, name, "# upstream\n")
        self.write(self.upstream, "function/__init__.py", "# loader\n")
        self.write(self.upstream, "function/auth.py", "def func_auth(): return 'upstream'\n")
        self.write(self.upstream, "docs/extend.md", "upstream docs\n")
        self.write(self.upstream, "config.py", "config_postgres = {}\nconfig_api = {}\n")
        self.write(self.upstream, "requirements.txt", "fastapi==1.0\norjson==3.0\n")
        self.commit(self.upstream)
        self.root = self.base / "developer"
        self.git(self.base, "clone", str(self.upstream), str(self.root))
        self.write(self.root, "function/custom_tracked.py", "def func_custom(): return 7\n")
        self.commit(self.root)
        self.write(self.root, "function/custom_untracked.py", "def func_other(): return 8\n")
        self.write(self.root, "function/auth.py", "def func_auth(): return 'local edit'\n")
        self.write(self.root, "requirements.txt", "fastapi==0.9\nmy-package==2.0\n")
        self.write(self.root, "config_extend.py", "config_api: dict = {'custom': True}\n")
        self.write(self.root, ".env", "CUSTOM=preserve\n")
        self.output = io.StringIO()
        self.addCleanup(self.output.close)
        self.stdout = redirect_stdout(self.output)
        self.stderr = redirect_stderr(self.output)
        self.stdout.__enter__()
        self.stderr.__enter__()
        self.addCleanup(self.stdout.__exit__, None, None, None)
        self.addCleanup(self.stderr.__exit__, None, None, None)

    def git(self, root, *args):
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True).stdout

    def write(self, root, name, text):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def commit(self, root):
        self.git(root, "add", "-A")
        self.git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "fixture")

    def run_sync(self):
        return sync.sync(self.root, str(self.upstream))

    def snapshot(self):
        return {str(p.relative_to(self.root)): (p.read_bytes(), p.stat().st_mode & 0o777)
                for p in self.root.rglob("*") if p.is_file()
                and p.relative_to(self.root).parts[0] not in (".git", ".atom-sync")}

    def test_sync_creates_replaces_preserves_without_backup_files(self):
        (self.root / "function/__init__.py").unlink()
        before = self.snapshot()
        index = (self.root / ".git/index").read_bytes()
        self.run_sync()
        self.assertEqual((self.root / ".git/index").read_bytes(), index)
        self.assertTrue((self.root / "function/__init__.py").exists())
        self.assertIn("upstream", (self.root / "function/auth.py").read_text())
        for name in ("function/custom_tracked.py", "function/custom_untracked.py", ".env"):
            self.assertEqual(self.snapshot()[name], before[name])
        self.assertEqual((self.root / "requirements.txt").read_text(), "fastapi==0.9\nmy-package==2.0\norjson==3.0\n")
        extension = (self.root / "config_extend.py").read_text()
        self.assertIn("config_api: dict = {'custom': True}", extension)
        self.assertEqual(extension.count("config_api"), 1)
        self.assertIn("config_postgres = {}", extension)
        state = json.loads((self.root / sync.STATE_PATH).read_text())
        self.assertNotIn("function/custom_tracked.py", state["files"])
        self.assertIn("function/auth.py", state["files"])
        self.assertEqual({p.name for p in (self.root / ".atom-sync").iterdir()}, {"state.json"})

    def test_fetch_failure_does_not_use_stale_fetch_head(self):
        self.run_sync()
        before = self.snapshot()
        state = (self.root / sync.STATE_PATH).read_bytes()
        with self.assertRaises(subprocess.CalledProcessError):
            sync.sync(self.root, str(self.base / "missing-repository"))
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((self.root / sync.STATE_PATH).read_bytes(), state)
        self.assertFalse((self.root / ".atom-sync/lock").exists())

    def test_missing_upstream_file_stops_before_writes(self):
        (self.upstream / "main.py").unlink()
        self.commit(self.upstream)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "Required upstream path"):
            self.run_sync()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.root / sync.STATE_PATH).exists())

    def test_syntax_failure_stops_before_writes(self):
        self.write(self.upstream, "function/auth.py", "def invalid(:\n")
        self.commit(self.upstream)
        before = self.snapshot()
        with self.assertRaises(SyntaxError):
            self.run_sync()
        self.assertEqual(self.snapshot(), before)

    def test_write_failure_restores_files_and_does_not_advance_state(self):
        before = self.snapshot()
        original = sync.atomic_write
        failed = False
        def fail_once(path, *args):
            nonlocal failed
            if path == self.root / "main.py" and not failed:
                failed = True
                raise OSError("simulated write failure")
            return original(path, *args)
        with patch.object(sync, "atomic_write", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "simulated write failure"):
                self.run_sync()
        self.assertTrue(failed)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.root / sync.STATE_PATH).exists())
        self.assertIn("previous files restored", self.output.getvalue())

    def test_renamed_owned_module_is_retired_but_custom_files_survive(self):
        self.run_sync()
        self.git(self.upstream, "mv", "function/auth.py", "function/login.py")
        self.commit(self.upstream)
        self.run_sync()
        self.assertFalse((self.root / "function/auth.py").exists())
        self.assertTrue((self.root / "function/login.py").exists())
        self.assertTrue((self.root / "function/custom_tracked.py").exists())

    def test_late_failure_restores_removed_files_and_previous_state(self):
        self.run_sync()
        self.git(self.upstream, "mv", "function/auth.py", "function/login.py")
        self.commit(self.upstream)
        before = self.snapshot()
        state = (self.root / sync.STATE_PATH).read_bytes()
        original = sync.atomic_write
        failed = False
        def fail_once(path, *args):
            nonlocal failed
            if path == self.root / sync.STATE_PATH and not failed:
                failed = True
                raise OSError("state write failure")
            return original(path, *args)
        with patch.object(sync, "atomic_write", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "state write failure"):
                self.run_sync()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((self.root / sync.STATE_PATH).read_bytes(), state)

    def test_modified_retired_file_stops_update(self):
        self.run_sync()
        self.write(self.root, "function/auth.py", "# developer edits\n")
        (self.upstream / "function/auth.py").unlink()
        self.commit(self.upstream)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "Retired Atom file has local edits"):
            self.run_sync()
        self.assertEqual(self.snapshot(), before)

    def test_symlink_cannot_redirect_update_outside_project(self):
        outside = self.base / "outside.py"
        outside.write_text("# keep\n")
        (self.root / "function/auth.py").unlink()
        (self.root / "function/auth.py").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.run_sync()
        self.assertEqual(outside.read_text(), "# keep\n")

    def test_existing_lock_stops_before_fetch(self):
        (self.root / ".atom-sync").mkdir()
        (self.root / ".atom-sync/lock").write_text("other sync")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "Another sync"):
            self.run_sync()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((self.root / ".atom-sync/lock").read_text(), "other sync")

    def test_import_has_no_side_effects(self):
        result = subprocess.run([sys.executable, "-c", "import sync"],
                                cwd=Path(sync.__file__).parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
