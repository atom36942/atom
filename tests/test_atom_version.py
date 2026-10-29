"""Atom's version, read from the project's sync.py."""

from pathlib import Path
import tempfile
import unittest

from function.app import func_atom_version


class AtomVersionTests(unittest.TestCase):
    def test_version_comes_from_sync_py(self):
        self.assertRegex(func_atom_version(path=str(Path(__file__).resolve().parents[1] / "sync.py")), r"^\d+\.\d+\.\d+$")

    def test_missing_or_older_sync_py_has_no_version(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(func_atom_version(path=f"{directory}/sync.py"))
            Path(directory, "sync.py").write_text("# from before versions\n")
            self.assertIsNone(func_atom_version(path=f"{directory}/sync.py"))
