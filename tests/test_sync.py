"""Updater integration tests use disposable local Git repositories only."""

from contextlib import redirect_stdout
from contextlib import redirect_stderr
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock
from unittest.mock import patch

import sync


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        no_network = patch.object(sync, "pypi_latest", lambda *, name: None)    # tests never call PyPI
        no_network.start(); self.addCleanup(no_network.stop)
        self.base = Path(self.temp.name).resolve()
        self.upstream = self.base / "upstream"
        self.upstream.mkdir()
        self.git(self.upstream, "init", "-b", "main")
        for name in sync.FILES_TO_SYNC:
            if name in sync.SYNC_FOLDERS:
                continue
            self.write(self.upstream, name, "# upstream\n")
        self.write(self.upstream, "function/__init__.py", "# loader\n")
        self.write(self.upstream, "function/auth.py", "def func_auth(): return 'upstream'\n")
        self.write(self.upstream, "router/index.py", "# upstream router\n")
        self.write(self.upstream, "docs/extend.md", "upstream docs\n")
        self.write(self.upstream, "tests/test_example.py", "# upstream test\n")
        self.write(self.upstream, "script/worker.py", "# upstream worker\n")
        self.write(self.upstream, "static/api.html", "upstream api page\n")
        self.write(self.upstream, "files/README.md", "upstream files\n")
        self.write(self.upstream, "config.py", "config_postgres = {}\nconfig_api = {}\n")
        self.write(self.upstream, "requirements.txt", "fastapi==1.0\norjson==3.0\n")
        self.commit(self.upstream)
        self.root = self.base / "developer"
        self.git(self.base, "clone", str(self.upstream), str(self.root))
        self.write(self.root, "function_extend/custom_tracked.py", "def func_custom(): return 7\n")
        self.write(self.root, "router_extend/custom_tracked.py", "# developer router\n")
        self.commit(self.root)
        self.write(self.root, "function_extend/custom_untracked.py", "def func_other(): return 8\n")
        self.write(self.root, "router_extend/custom_untracked.py", "# untracked developer router\n")
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
        return sync.sync(root=self.root, repo_url=str(self.upstream))

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
        for name in ("function_extend/custom_tracked.py", "function_extend/custom_untracked.py", "router_extend/custom_tracked.py", "router_extend/custom_untracked.py", ".env"):
            self.assertEqual(self.snapshot()[name], before[name])
        self.assertEqual((self.root / "requirements.txt").read_text(), self.requirements(["fastapi==1.0", "orjson==3.0"], ["my-package==2.0"]))
        self.assertEqual(self.snapshot()["config_extend.py"], before["config_extend.py"])
        state = json.loads((self.root / sync.STATE_PATH).read_text())
        self.assertNotIn("function_extend/custom_tracked.py", state["files"])
        self.assertNotIn("router_extend/custom_tracked.py", state["files"])
        self.assertNotIn("router_extend/custom_untracked.py", state["files"])
        self.assertIn("router/index.py", state["files"])
        self.assertIn("function/auth.py", state["files"])
        self.assertEqual({p.name for p in (self.root / ".atom-sync").iterdir()}, {"state.json"})

    def test_version_is_read_from_sync_source(self):
        self.assertEqual(sync.atom_version(source=b'# x\nATOM_VERSION = "1.2.0"\n'), "1.2.0")
        self.assertIsNone(sync.atom_version(source=b"# a sync.py from before versions\n"))
        self.assertRegex(sync.atom_version(source=Path(sync.__file__).read_bytes()), r"^\d+\.\d+\.\d+$")

    def test_version_change_lines(self):
        self.assertEqual(sync.version_change(old="1.2.0", new="1.3.0", is_same_revision=False), "Atom 1.2.0 -> 1.3.0")
        self.assertEqual(sync.version_change(old=None, new="1.3.0", is_same_revision=False), "Atom unknown (synced before versions) -> 1.3.0")
        self.assertEqual(sync.version_change(old="1.3.0", new="1.3.0", is_same_revision=True), "Already on Atom 1.3.0")
        self.assertEqual(sync.version_change(old="1.3.0", new="1.3.0", is_same_revision=False), "Atom 1.3.0 (newer commits on main)")

    def test_status_shows_both_versions_and_changes_nothing(self):
        self.write(self.upstream, "sync.py", 'ATOM_VERSION = "1.3.0"\n')
        self.commit(self.upstream)
        self.write(self.root, "sync.py", 'ATOM_VERSION = "1.2.0"\n')
        before = self.snapshot()
        sync.status(root=self.root, repo_url=str(self.upstream))
        self.assertIn("This project: Atom 1.2.0", self.output.getvalue())
        self.assertIn("Latest on main: Atom 1.3.0", self.output.getvalue())
        self.assertIn("Run python3 sync.py to update.", self.output.getvalue())
        self.assertEqual(self.snapshot(), before)

    def test_sync_creates_missing_config_extension(self):
        (self.root / "config_extend.py").unlink()
        self.run_sync()
        self.assertEqual((self.root / "config_extend.py").read_text(), sync.EXTEND_FILES["config_extend.py"])

    def test_sync_preserves_empty_or_invalid_config_extension(self):
        for content in ("", "config_postgres = None\n", "not valid python: !!!\n"):
            with self.subTest(content=content):
                self.write(self.root, "config_extend.py", content)
                self.run_sync()
                self.assertEqual((self.root / "config_extend.py").read_text(), content)

    def test_sync_leaves_tests_folder_untouched(self):
        self.write(self.root, "tests/test_example.py", "# developer test\n")
        self.write(self.root, "tests/local_test.py", "# local test\n")
        self.write(self.upstream, "tests/new_test.py", "# upstream new test\n")
        self.commit(self.upstream)
        self.run_sync()
        self.assertEqual((self.root / "tests/test_example.py").read_text(), "# developer test\n")
        self.assertEqual((self.root / "tests/local_test.py").read_text(), "# local test\n")
        self.assertFalse((self.root / "tests/new_test.py").exists())

    def test_fetch_failure_does_not_use_stale_fetch_head(self):
        self.run_sync()
        before = self.snapshot()
        state = (self.root / sync.STATE_PATH).read_bytes()
        with self.assertRaises(subprocess.CalledProcessError):
            sync.sync(root=self.root, repo_url=str(self.base / "missing-repository"))
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
        def fail_once(*, path, content, mode):
            nonlocal failed
            if path == self.root / "main.py" and not failed:
                failed = True
                raise OSError("simulated write failure")
            return original(path=path, content=content, mode=mode)
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
        self.assertTrue((self.root / "function_extend/custom_tracked.py").exists())

    def test_all_atom_folders_are_mirrored_on_first_run(self):
        for folder in sync.SYNC_FOLDERS:
            self.write(self.root, f"{folder}/local/nested.py", "# local only\n")
            self.write(self.upstream, f"{folder}/new.py", "# upstream new\n")
        self.commit(self.upstream)
        self.run_sync()
        for folder in sync.SYNC_FOLDERS:
            self.assertFalse((self.root / folder / "local").exists())
            self.assertEqual((self.root / folder / "new.py").read_text(), "# upstream new\n")

    def test_late_failure_restores_removed_files_and_previous_state(self):
        self.run_sync()
        self.git(self.upstream, "mv", "function/auth.py", "function/login.py")
        self.commit(self.upstream)
        before = self.snapshot()
        state = (self.root / sync.STATE_PATH).read_bytes()
        original = sync.atomic_write
        failed = False
        def fail_once(*, path, content, mode):
            nonlocal failed
            if path == self.root / sync.STATE_PATH and not failed:
                failed = True
                raise OSError("state write failure")
            return original(path=path, content=content, mode=mode)
        with patch.object(sync, "atomic_write", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "state write failure"):
                self.run_sync()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((self.root / sync.STATE_PATH).read_bytes(), state)

    def test_modified_retired_file_is_removed(self):
        self.run_sync()
        self.write(self.root, "function/auth.py", "# developer edits\n")
        (self.upstream / "function/auth.py").unlink()
        self.commit(self.upstream)
        self.run_sync()
        self.assertFalse((self.root / "function/auth.py").exists())

    def test_removed_sync_selection_is_preserved_and_forgotten(self):
        self.write(self.upstream, "extra/pulse.html", "upstream pulse\n")
        self.commit(self.upstream)
        for content in ("upstream pulse\n", "developer pulse\n", None):
            with self.subTest(content=content):
                with patch.object(sync, "FILES_TO_SYNC", [*sync.FILES_TO_SYNC, "extra/pulse.html"]):
                    self.run_sync()
                path = self.root / "extra/pulse.html"
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
                self.assertNotIn("extra/pulse.html", state["files"])

    def test_missing_extend_paths_are_created_and_existing_ones_kept(self):
        self.run_sync()
        for name in sync.EXTEND_FOLDERS:
            self.assertTrue((self.root / name).is_dir())
        self.assertEqual((self.root / "tests_extend/__init__.py").read_text(), "")
        self.assertEqual([p.name for p in (self.root / "files_extend").iterdir()], ["readme.md"])
        self.assertEqual((self.root / "config_extend.py").read_text(), "config_api: dict = {'custom': True}\n")
        self.assertEqual({p.name for p in (self.root / "function_extend").iterdir()}, {"custom_tracked.py", "custom_untracked.py", "readme.md"})
        for name in sync.EXTEND_FOLDERS:
            self.assertEqual((self.root / name / "readme.md").read_text(), sync.EXTEND_README[name])
        (self.root / "tests_extend/__init__.py").unlink()
        (self.root / "script_extend/readme.md").unlink()
        self.write(self.root, "static_extend/readme.md", "# mine\n")
        self.run_sync()
        self.assertEqual((self.root / "tests_extend/__init__.py").read_text(), "")    # recreated, like every missing starter file
        self.assertEqual((self.root / "script_extend/readme.md").read_text(), sync.EXTEND_README["script_extend"])
        self.assertEqual((self.root / "static_extend/readme.md").read_text(), "# mine\n")

    def test_missing_env_gets_the_commented_starter_and_an_existing_one_is_kept(self):
        self.run_sync()
        self.assertEqual((self.root / ".env").read_text(), "CUSTOM=preserve\n")
        (self.root / ".env").unlink()
        self.run_sync()
        self.assertEqual((self.root / ".env").read_text(), sync.EXTEND_FILES[".env"])
        if os.name != "nt": self.assertEqual((self.root / ".env").stat().st_mode & 0o777, 0o600)
        self.assertTrue(all(line.startswith("#") for line in sync.ENV_STARTER.splitlines()))

    def test_extensions_are_never_written_even_when_upstream_has_them(self):
        extensions = ["docs_extend", "router_extend", "function_extend", "script_extend", "static_extend", "files_extend", "tests_extend", "config_extend.py"]
        for name in extensions:
            path = name if name.endswith(".py") else f"{name}/custom.py"
            self.write(self.root, path, "# developer\n")
            self.write(self.upstream, path, "# upstream collision\n")
        self.commit(self.upstream)
        self.run_sync()
        for name in extensions:
            path = name if name.endswith(".py") else f"{name}/custom.py"
            self.assertEqual((self.root / path).read_text(), "# developer\n")

    def test_removed_router_selection_preserves_its_files(self):
        self.run_sync()
        self.write(self.root, "router/index.py", "# developer edits\n")
        with patch.object(sync, "FILES_TO_SYNC", [p for p in sync.FILES_TO_SYNC if p != "router"]):
            self.run_sync()
        self.assertEqual((self.root / "router/index.py").read_text(), "# developer edits\n")

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

    def requirements(self, atom, extend):
        return "\n".join([sync.REQUIREMENTS_ATOM_HEADER, *atom, "", sync.REQUIREMENTS_EXTEND_HEADER, *extend]) + "\n"

    def test_gitignore_keeps_project_extend_lines_and_resets_atom_part(self):
        upstream = "*\n!main.py\n\n# extend\n"
        local = "*\n!main.py\n!my-edit\n\n# extend\n# a note\n!infra/\n\n!infra/**\n"
        self.assertEqual(sync.merge_gitignore(local=local, upstream=upstream), "*\n!main.py\n\n# extend\n!infra/\n!infra/**\n")

    def test_gitignore_without_extend_section_gets_atom_version(self):
        upstream = "*\n!main.py\n\n# extend\n"
        self.assertEqual(sync.merge_gitignore(local="*\n!infra/\n", upstream=upstream), upstream)
        self.assertEqual(sync.merge_gitignore(local=None, upstream=upstream), upstream)

    def test_requirements_are_created_from_atom_with_an_empty_extend_section(self):
        self.assertEqual(sync.merge_requirements(local=None, upstream="fastapi==1.0\norjson==3.0"), (self.requirements(["fastapi==1.0", "orjson==3.0"], []), []))

    def test_requirements_file_without_sections_keeps_project_lines_as_extend(self):
        local = "# project deps\nFastAPI==0.9  # old pin\nmy-package==2.0\n-e ./libs/tool\npyjwt>=2.0\npandas\n"
        upstream = "fastapi==1.0\nPyJWT==2.15.1\norjson==3.0\n"
        text, notes = sync.merge_requirements(local=local, upstream=upstream)
        self.assertEqual(text, self.requirements(["fastapi==1.0", "PyJWT==2.15.1", "orjson==3.0"], ["-e ./libs/tool", "my-package==2.0", "pandas"]))
        self.assertEqual(notes, ["removed '# project deps' from # extend: the section holds package lines only", "removed 'FastAPI==0.9  # old pin' from # extend: Atom installs fastapi==1.0", "removed 'pyjwt>=2.0' from # extend: Atom installs PyJWT==2.15.1", "'pandas' in # extend is not pinned with =="])

    def test_requirements_atom_section_is_replaced_and_packages_atom_dropped_are_removed(self):
        local = self.requirements(["fastapi==0.9", "my-edit==1.0"], ["pandas==2.2.0", "", "# reports", "openpyxl==3.1.5"])
        text, notes = sync.merge_requirements(local=local, upstream=self.requirements(["fastapi==1.0", "orjson==3.0"], []))
        self.assertEqual(text, self.requirements(["fastapi==1.0", "orjson==3.0"], ["openpyxl==3.1.5", "pandas==2.2.0"]))    # flat and sorted; my-edit was Atom's, Atom dropped it
        self.assertEqual(notes, ["removed 'my-edit==1.0': Atom no longer uses it; add it to # extend if your project does", "removed '# reports' from # extend: the section holds package lines only"])

    def test_requirements_extend_line_for_an_atom_package_is_removed_and_reported_with_atom_version(self):
        text, notes = sync.merge_requirements(local=self.requirements(["fastapi==1.0"], ["Python_Multipart==0.0.20", "pandas==2.2.0"]), upstream=self.requirements(["fastapi==1.0", "python-multipart==0.0.32"], []))
        self.assertEqual(text, self.requirements(["fastapi==1.0", "python-multipart==0.0.32"], ["pandas==2.2.0"]))
        self.assertEqual(notes, ["removed 'Python_Multipart==0.0.20' from # extend: Atom installs python-multipart==0.0.32"])

    def test_requirements_duplicates_keep_the_last_line_and_unpinned_lines_are_reported(self):
        text, notes = sync.merge_requirements(local=self.requirements([], ["pandas==2.0", "duckdb>=1", "Pandas==2.2"]), upstream=self.requirements(["fastapi==1.0"], []))
        self.assertEqual(text, self.requirements(["fastapi==1.0"], ["duckdb>=1", "Pandas==2.2"]))
        self.assertEqual(notes, ["pandas was listed twice in # extend; kept 'Pandas==2.2'", "'duckdb>=1' in # extend is not pinned with =="])

    def test_requirements_package_in_both_sections_keeps_the_extend_pin(self):
        text, notes = sync.merge_requirements(local=self.requirements(["fastapi==1.0", "pandas==1.0"], ["pandas==2.2"]), upstream=self.requirements(["fastapi==1.0"], []))
        self.assertEqual((text, notes), (self.requirements(["fastapi==1.0"], ["pandas==2.2"]), []))

    def test_requirements_second_merge_changes_nothing(self):
        upstream = self.requirements(["fastapi==1.0"], [])
        text, _ = sync.merge_requirements(local="fastapi==0.9\nmy-package==2.0\n", upstream=upstream)
        self.assertEqual(sync.merge_requirements(local=text, upstream=upstream), (text, []))

    def test_cli_flags_reach_the_updater(self):
        for argv, venv, outdated in ([], True, True), (["--no-venv"], False, True), (["--no-outdated"], True, False), (["--no-outdated", "--no-venv"], False, False):
            with self.subTest(argv=argv), patch.object(sync.sys, "argv", ["sync.py", *argv]), patch.object(sync, "bootstrap_sync") as bootstrap:
                self.assertEqual(sync.main(), 0)
                self.assertEqual((bootstrap.call_args.kwargs["is_venv_sync"], bootstrap.call_args.kwargs["is_outdated_check"]), (venv, outdated))
        with patch.object(sync.sys, "argv", ["sync.py", "--other"]), redirect_stderr(io.StringIO()) as error:
            self.assertEqual(sync.main(), 1)
        self.assertIn("--no-outdated", error.getvalue())

    def test_outdated_extend_packages_are_reported_and_offline_is_silent(self):
        self.write(self.root, "requirements.txt", self.requirements(["fastapi==1.0"], ["pandas==3.0.2", "duckdb==1.5.5", "splink==4.0.17", "beta-tool==2.0.0rc1", "local-tool>=1"]))
        latest = {"pandas": "3.1.0", "duckdb": "1.5.5", "splink": "5.0.0", "beta-tool": "1.9.0"}
        output = io.StringIO()
        with patch.object(sync, "pypi_latest", lambda *, name: latest.get(name)), redirect_stdout(output):
            sync.extend_outdated_report(root=self.root)
        self.assertIn("pandas 3.0.2 -> 3.1.0\n", output.getvalue())
        self.assertIn("splink 4.0.17 -> 5.0.0 (major: check its release notes)", output.getvalue())
        self.assertNotIn("beta-tool", output.getvalue())    # a pre-release pinned above PyPI's latest is not a downgrade
        self.assertNotIn("duckdb", output.getvalue())
        self.assertNotIn("fastapi", output.getvalue())    # Atom's packages are Atom's business
        output = io.StringIO()
        with patch.object(sync, "pypi_latest", lambda *, name: None), redirect_stdout(output):
            sync.extend_outdated_report(root=self.root)
        self.assertEqual(output.getvalue(), "")

    def test_python_version_comes_from_the_dockerfile(self):
        self.write(self.root, "Dockerfile", "# base\nFROM python:3.14-slim\nRUN true\n")
        self.assertEqual(sync.python_version_required(root=self.root), "3.14")
        self.write(self.root, "Dockerfile", "FROM ubuntu:24.04\n")
        with self.assertRaisesRegex(ValueError, "FROM python"): sync.python_version_required(root=self.root)

    def fake_venv_tools(self, fail_on=None):
        """Stand-ins for python -m venv and pip: record commands, create the venv folder, optionally fail one step."""
        calls = []
        def run_command(*, args, cwd=None):
            calls.append(args[1:3] if args[1] == "-m" else args)
            if fail_on and fail_on in " ".join(str(a) for a in args): raise ValueError(f"{fail_on} failed (exit 1)")
            if args[1:3] == ["-m", "venv"]: (Path(args[3]) / "bin").mkdir(parents=True)
        return calls, run_command

    def test_venv_is_rebuilt_then_skipped_while_it_matches(self):
        self.write(self.root, "Dockerfile", "FROM python:3.14-slim\n")
        calls, run_command = self.fake_venv_tools()
        packages = {"value": b"fastapi==1.0\n"}
        freeze = lambda *, root, venv, version: {"python": version, "requirements": "r", "packages": packages["value"].decode()}
        with patch.object(sync, "run_command", run_command), patch.object(sync, "venv_fingerprint", freeze), patch.object(sync, "python_command", lambda *, version: ["python3.14"]):
            sync.sync_venv(root=self.root)
            self.assertEqual(calls, [["-m", "venv"], ["-m", "pip"], ["-m", "pip"]])
            calls.clear(); sync.sync_venv(root=self.root)
            self.assertEqual(calls, [])    # nothing changed: no rebuild
            packages["value"] = b"fastapi==1.0\nextra==9.9\n"    # someone pip-installed a package by hand
            sync.sync_venv(root=self.root)
            self.assertEqual(len(calls), 3)
        self.assertFalse((self.root / sync.VENV_OLD_DIR).exists())

    def test_failed_rebuild_restores_the_previous_venv(self):
        self.write(self.root, "Dockerfile", "FROM python:3.14-slim\n")
        self.write(self.root, "venv/marker.txt", "old venv\n")
        calls, run_command = self.fake_venv_tools(fail_on="requirements.txt")
        with patch.object(sync, "run_command", run_command), patch.object(sync, "python_command", lambda *, version: ["python3.14"]):
            with self.assertRaisesRegex(ValueError, "failed"): sync.sync_venv(root=self.root)
        self.assertEqual((self.root / "venv/marker.txt").read_text(), "old venv\n")
        self.assertFalse((self.root / sync.VENV_OLD_DIR).exists())

    def test_interrupted_rebuild_puts_the_old_venv_back(self):
        self.write(self.root, "Dockerfile", "FROM python:3.14-slim\n")
        self.write(self.root, "venv_old/marker.txt", "old venv\n")    # a previous rebuild stopped after moving venv away
        calls, run_command = self.fake_venv_tools(fail_on="venv")
        with patch.object(sync, "run_command", run_command), patch.object(sync, "python_command", lambda *, version: ["python3.14"]):
            with self.assertRaises(ValueError): sync.sync_venv(root=self.root)
        self.assertEqual((self.root / "venv/marker.txt").read_text(), "old venv\n")

    def test_venv_in_use_leaves_it_unchanged_with_clear_steps(self):
        self.write(self.root, "Dockerfile", "FROM python:3.14-slim\n")
        self.write(self.root, "venv/marker.txt", "old venv\n")
        calls, run_command = self.fake_venv_tools()
        real_rename = Path.rename
        def locked_rename(path, target):
            if path.name == sync.VENV_DIR: raise PermissionError("[WinError 32] being used by another process")
            return real_rename(path, target)
        with patch.object(sync, "run_command", run_command), patch.object(sync, "python_command", lambda *, version: ["python3.14"]), patch.object(Path, "rename", locked_rename):
            with self.assertRaisesRegex(ValueError, "venv is in use.*files are synced, the venv is unchanged.*py sync.py"): sync.sync_venv(root=self.root)
        self.assertEqual(calls, [])
        self.assertEqual((self.root / "venv/marker.txt").read_text(), "old venv\n")

    def test_locked_leftover_venv_old_stops_with_clear_steps(self):
        self.write(self.root, "Dockerfile", "FROM python:3.14-slim\n")
        self.write(self.root, "venv/marker.txt", "venv\n")
        self.write(self.root, "venv_old/marker.txt", "leftover\n")
        with patch.object(sync.shutil, "rmtree", lambda path, ignore_errors=False: None):
            with self.assertRaisesRegex(ValueError, "venv_old from an earlier rebuild is still in use"): sync.sync_venv(root=self.root)
        self.assertEqual((self.root / "venv/marker.txt").read_text(), "venv\n")

    def test_windows_sync_run_from_the_venv_is_stopped_before_touching_it(self):
        self.write(self.root, "Dockerfile", "FROM python:3.14-slim\n")
        self.write(self.root, "venv/marker.txt", "venv\n")
        with patch.object(sync.sys, "platform", "win32"), patch.object(sync.sys, "prefix", str(self.root / "venv")):
            with self.assertRaisesRegex(ValueError, "sync is running from venv.*py sync.py"): sync.sync_venv(root=self.root)
        self.assertEqual((self.root / "venv/marker.txt").read_text(), "venv\n")

    def test_venv_is_not_rebuilt_inside_a_cloud_synced_folder(self):
        root = self.root / "OneDrive - Example" / "project"
        self.write(root, "Dockerfile", "FROM python:3.14-slim\n")
        with patch.object(sync, "python_command", lambda *, version: ["python3.14"]), patch.object(sync, "run_command", Mock(side_effect=AssertionError("venv touched"))):
            with self.assertRaisesRegex(ValueError, "inside OneDrive - Example.*move the project"): sync.sync_venv(root=root)
        self.assertFalse((root / "venv").exists())

    def test_missing_python_names_how_to_install_it(self):
        with patch.object(sync.shutil, "which", lambda name: None):
            with self.assertRaisesRegex(ValueError, "Python 9.99 .*not installed: macOS: brew install python@9.99"): sync.python_command(version="9.99")

    def test_windows_launcher_without_the_version_names_how_to_install_it(self):
        which = lambda name: "py.exe" if name == "py" else None
        with patch.object(sync.sys, "platform", "win32"), patch.object(sync.shutil, "which", which), patch.object(sync.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 103)):
            with self.assertRaisesRegex(ValueError, "Python 9.99 .*not installed: install it from python.org"): sync.python_command(version="9.99")
        with patch.object(sync.sys, "platform", "win32"), patch.object(sync.shutil, "which", which), patch.object(sync.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0)):
            self.assertEqual(sync.python_command(version="9.99"), ["py", "-9.99"])

    def test_import_has_no_side_effects(self):
        result = subprocess.run([sys.executable, "-c", "import sync"],
                                cwd=Path(sync.__file__).parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def install_bootstrap_fixture(self):
        source = Path(sync.__file__).read_text()
        # The child must not fetch: its repository URL is deliberately unusable.
        latest = source.replace('SYNC_FILES = [', 'SYNC_FILES = [\n    "latest-only.txt",', 1)
        latest = latest.replace(f'REPO_URL = "{sync.REPO_URL}"', 'REPO_URL = "/missing/child-must-not-fetch"')
        self.write(self.upstream, "sync.py", latest)
        self.write(self.upstream, "latest-only.txt", "synced by the newest rules\n")
        self.commit(self.upstream)
        local = source.replace(f'REPO_URL = "{sync.REPO_URL}"', f'REPO_URL = {str(self.upstream)!r}')
        local = local.replace('def prepare_update(*, root, revision):',
                              'def prepare_update(*, root, revision):\n    raise RuntimeError("old sync logic must not run")')
        self.write(self.root, "sync.py", local)
        return latest

    def run_cli(self):
        return subprocess.run([sys.executable, str(self.root / "sync.py"), "--no-venv", "--no-outdated"], cwd=self.root,
                              capture_output=True, text=True, timeout=30)

    def test_cli_restarts_latest_updater_and_applies_new_rules_in_one_run(self):
        latest = self.install_bootstrap_fixture()
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "sync.py").read_text(), latest)
        self.assertEqual((self.root / "latest-only.txt").read_text(), "synced by the newest rules\n")
        self.assertEqual(result.stdout.count("Fetching Atom main..."), 1)
        self.assertEqual(result.stdout.count("Running the latest Atom updater..."), 1)
        self.assertIn(f"Atom {sync.ATOM_VERSION} (newer commits on main)", result.stdout)
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
        self.assertIn("run python3 sync.py again", first.stderr)
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
        with sync.sync_lock(root=self.root) as token:
            for supplied in ("", "wrong-token"):
                with self.subTest(token=supplied), patch.dict(os.environ, {sync.LOCK_TOKEN_ENV: supplied}):
                    with patch.object(sync, "apply_revision") as apply:
                        with self.assertRaisesRegex(ValueError, "parent updater's lock"):
                            sync.apply_bootstrapped_revision(root=self.root, revision=revision)
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
        self.assertIn(f"sync.py now shows Atom {sync.ATOM_VERSION}, but the other files may not be updated", result.stderr)
        self.assertIn("run python3 sync.py again", result.stderr)
        self.assertFalse((self.root / ".atom-sync/lock").exists())

    def test_internal_child_mode_rejects_missing_parent_lock(self):
        revision = self.git(self.root, "rev-parse", "HEAD").decode().strip()
        with self.assertRaisesRegex(ValueError, "parent updater's lock"):
            sync.apply_bootstrapped_revision(root=self.root, revision=revision)


if __name__ == "__main__":
    unittest.main()
