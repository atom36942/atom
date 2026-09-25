"""Updater integration tests use disposable local Git repositories only."""

from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
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
            if name in ("function", "router", "docs"):
                continue
            self.write(self.upstream, name, "# upstream\n")
        self.write(self.upstream, "function/__init__.py", "# loader\n")
        self.write(self.upstream, "function/auth.py", "def func_auth(): return 'upstream'\n")
        self.write(self.upstream, "router/index.py", "# upstream router\n")
        self.write(self.upstream, "docs/extend.md", "upstream docs\n")
        self.write(self.upstream, "config.py", "config_postgres = {}\nconfig_api = {}\n")
        self.write(self.upstream, "requirements.txt", "fastapi==1.0\norjson==3.0\n")
        self.commit(self.upstream)
        self.root = self.base / "developer"
        self.git(self.base, "clone", str(self.upstream), str(self.root))
        self.write(self.root, "function/custom_tracked.py", "def func_custom(): return 7\n")
        self.write(self.root, "router/custom_tracked.py", "# developer router\n")
        self.commit(self.root)
        self.write(self.root, "function/custom_untracked.py", "def func_other(): return 8\n")
        self.write(self.root, "router/custom_untracked.py", "# untracked developer router\n")
        self.write(self.root, "function/auth.py", "def func_auth(): return 'local edit'\n")
        self.write(self.root, "router/index.py", "# local edit\n")
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
        self.assertEqual((self.root / "router/index.py").read_text(), "# upstream router\n")
        for name in ("function/custom_tracked.py", "function/custom_untracked.py", "router/custom_tracked.py", "router/custom_untracked.py", ".env"):
            self.assertEqual(self.snapshot()[name], before[name])
        self.assertEqual((self.root / "requirements.txt").read_text(), "fastapi==0.9\nmy-package==2.0\norjson==3.0\n")
        extension = (self.root / "config_extend.py").read_text()
        self.assertIn("config_api: dict = {'custom': True}", extension)
        self.assertEqual(extension.count("config_api"), 1)
        self.assertIn("config_postgres = {}", extension)
        state = json.loads((self.root / sync.STATE_PATH).read_text())
        self.assertNotIn("function/custom_tracked.py", state["files"])
        self.assertNotIn("router/custom_tracked.py", state["files"])
        self.assertNotIn("router/custom_untracked.py", state["files"])
        self.assertIn("router/index.py", state["files"])
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

    def test_new_and_renamed_upstream_routers_sync_without_listing_individual_files(self):
        self.run_sync()
        self.git(self.upstream, "mv", "router/index.py", "router/home.py")
        self.write(self.upstream, "router/reports.py", "# newly shipped router\n")
        self.commit(self.upstream)
        self.run_sync()
        self.assertFalse((self.root / "router/index.py").exists())
        self.assertEqual((self.root / "router/home.py").read_text(), "# upstream router\n")
        self.assertEqual((self.root / "router/reports.py").read_text(), "# newly shipped router\n")
        self.assertEqual((self.root / "router/custom_tracked.py").read_text(), "# developer router\n")
        self.assertEqual((self.root / "router/custom_untracked.py").read_text(), "# untracked developer router\n")

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

    def test_removed_sync_selection_is_preserved_and_forgotten(self):
        self.write(self.upstream, "static/pulse.html", "upstream pulse\n")
        self.commit(self.upstream)
        for content in ("upstream pulse\n", "developer pulse\n", None):
            with self.subTest(content=content):
                with patch.object(sync, "files_to_sync", [*sync.files_to_sync, "static/pulse.html"]):
                    self.run_sync()
                path = self.root / "static/pulse.html"
                if content is None:
                    path.unlink()
                else:
                    path.write_text(content)
                self.run_sync()
                if content is None:
                    self.assertFalse(path.exists())
                else:
                    self.assertEqual(path.read_text(), content)
                state = json.loads((self.root / sync.STATE_PATH).read_text())
                self.assertNotIn("static/pulse.html", state["files"])

    def test_removed_folder_selection_preserves_its_files(self):
        self.run_sync()
        self.write(self.root, "router/index.py", "# developer edits\n")
        with patch.object(sync, "files_to_sync", [p for p in sync.files_to_sync if p != "router"]):
            self.run_sync()
        self.assertEqual((self.root / "router/index.py").read_text(), "# developer edits\n")
        state = json.loads((self.root / sync.STATE_PATH).read_text())
        self.assertFalse(any(name.startswith("router/") for name in state["files"]))

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

    def install_bootstrap_fixture(self):
        source = Path(sync.__file__).read_text()
        # The child must not fetch: its repository URL is deliberately unusable.
        latest = source.replace('files_to_sync = [', 'files_to_sync = [\n    "latest-only.txt",', 1)
        latest = latest.replace(f'REPO_URL = "{sync.REPO_URL}"', 'REPO_URL = "/missing/child-must-not-fetch"')
        self.write(self.upstream, "sync.py", latest)
        self.write(self.upstream, "latest-only.txt", "synced by the newest rules\n")
        self.commit(self.upstream)
        local = source.replace(f'REPO_URL = "{sync.REPO_URL}"', f'REPO_URL = {str(self.upstream)!r}')
        local = local.replace('def prepare_update(root, revision):',
                              'def prepare_update(root, revision):\n    raise RuntimeError("old sync logic must not run")')
        self.write(self.root, "sync.py", local)
        return latest

    def run_cli(self):
        return subprocess.run([sys.executable, str(self.root / "sync.py")], cwd=self.root,
                              capture_output=True, text=True, timeout=30)

    def test_cli_restarts_latest_updater_and_applies_new_rules_in_one_run(self):
        latest = self.install_bootstrap_fixture()
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "sync.py").read_text(), latest)
        self.assertEqual((self.root / "latest-only.txt").read_text(), "synced by the newest rules\n")
        self.assertEqual(result.stdout.count("Fetching Atom main..."), 1)
        self.assertEqual(result.stdout.count("Running the latest Atom updater..."), 1)
        self.assertEqual(result.stdout.count("Files synced successfully!"), 1)
        self.assertFalse((self.root / ".atom-sync/lock").exists())
        state = json.loads((self.root / sync.STATE_PATH).read_text())
        self.assertEqual(state["revision"], self.git(self.upstream, "rev-parse", "HEAD").decode().strip())

    def test_invalid_latest_updater_leaves_local_files_unchanged(self):
        self.install_bootstrap_fixture()
        self.write(self.upstream, "sync.py", "def invalid(:\n")
        self.commit(self.upstream)
        before = self.snapshot()
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.snapshot(), before)
        self.assertNotIn("Files synced successfully!", result.stdout)
        self.assertFalse((self.root / ".atom-sync/lock").exists())

    def test_child_accepts_handoff_with_different_parent_pid(self):
        latest = self.install_bootstrap_fixture()
        # Simulate the parent PID exposed behind a Windows venv launcher.
        latest = latest.replace('import os\n', 'import os\nos.getppid = lambda: -1\n', 1)
        self.write(self.upstream, "sync.py", latest)
        self.commit(self.upstream)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "latest-only.txt").read_text(), "synced by the newest rules\n")
        self.assertFalse((self.root / ".atom-sync/lock").exists())

    def test_old_updater_installs_token_updater_then_retry_succeeds(self):
        latest = self.install_bootstrap_fixture()
        local = self.root / "sync.py"
        # The previous updater launched the child without a handoff token.
        source = local.read_text().replace(', cwd=root, env=child_env)', ', cwd=root)')
        source = source.replace('stream.write(token)', 'stream.write(str(os.getpid()))')
        local.write_text(source)
        with patch.dict(os.environ):
            os.environ.pop(sync.LOCK_TOKEN_ENV, None)
            first = self.run_cli()
        self.assertNotEqual(first.returncode, 0)
        self.assertIn("no handoff token was received", first.stderr)
        self.assertIn("run python sync.py again", first.stderr)
        self.assertEqual(local.read_text(), latest)
        self.assertFalse((self.root / ".atom-sync/lock").exists())
        # The fixture's upstream URL is deliberately invalid for child fetches;
        # point the newly installed updater at the local repository for retry.
        local.write_text(latest.replace('REPO_URL = "/missing/child-must-not-fetch"',
                                        f'REPO_URL = {str(self.upstream)!r}'))
        second = self.run_cli()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual((self.root / "latest-only.txt").read_text(), "synced by the newest rules\n")

    def test_child_rejects_missing_or_wrong_handoff_token(self):
        revision = self.git(self.root, "rev-parse", "HEAD").decode().strip()
        with sync.sync_lock(self.root) as token:
            for supplied in ("", "wrong-token"):
                with self.subTest(token=supplied), patch.dict(os.environ, {sync.LOCK_TOKEN_ENV: supplied}):
                    with patch.object(sync, "apply_revision") as apply:
                        with self.assertRaisesRegex(ValueError, "parent updater's lock"):
                            sync.apply_bootstrapped_revision(self.root, revision)
                        apply.assert_not_called()
                self.assertEqual((self.root / ".atom-sync/lock").read_text(), token)

    def test_latest_updater_failure_is_reported_without_syncing_other_files(self):
        latest = self.install_bootstrap_fixture()
        (self.upstream / "main.py").unlink()
        self.commit(self.upstream)
        before = self.snapshot()
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        after = self.snapshot()
        before.pop("sync.py")
        after.pop("sync.py")
        self.assertEqual(after, before)
        self.assertEqual((self.root / "sync.py").read_text(), latest)
        self.assertNotIn("Files synced successfully!", result.stdout)
        self.assertFalse((self.root / ".atom-sync/lock").exists())

    def test_internal_child_mode_rejects_missing_parent_lock(self):
        revision = self.git(self.root, "rev-parse", "HEAD").decode().strip()
        with self.assertRaisesRegex(ValueError, "parent updater's lock"):
            sync.apply_bootstrapped_revision(self.root, revision)


if __name__ == "__main__":
    unittest.main()
