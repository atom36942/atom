"""sync.py's venv rebuild with real Python, venv and pip on this machine (set ATOM_TEST_VENV_REAL=1; needs network for pip).

CI runs it on Linux and macOS: the paths and the Python lookup differ per system.
"""
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import sync


@unittest.skipUnless(os.environ.get("ATOM_TEST_VENV_REAL"), "set ATOM_TEST_VENV_REAL=1 to build real venvs (slow, needs network)")
class RealVenvTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "Dockerfile").write_text(f"FROM python:{sys.version_info.major}.{sys.version_info.minor}-slim\n")
        self.requirements("six==1.17.0")

    def requirements(self, *atom):
        (self.root / "requirements.txt").write_text("\n".join([sync.REQUIREMENTS_ATOM_HEADER, *atom, "", sync.REQUIREMENTS_EXTEND_HEADER]) + "\n")

    def run_sync(self):
        output = io.StringIO()
        with redirect_stdout(output): sync.sync_venv(self.root)
        return output.getvalue()

    def packages(self):
        return subprocess.run([str(sync.venv_python(self.root / sync.VENV_DIR)), "-m", "pip", "freeze"], capture_output=True, text=True, check=True).stdout.split()

    def test_venv_is_built_skipped_cleaned_and_restored(self):
        self.assertIn("venv rebuilt", self.run_sync())
        self.assertEqual(self.packages(), ["six==1.17.0"])
        self.assertIn("already matches", self.run_sync())
        subprocess.run([str(sync.venv_python(self.root / sync.VENV_DIR)), "-m", "pip", "install", "--quiet", "idna==3.10"], check=True)
        self.assertIn("venv rebuilt", self.run_sync())    # a hand-installed package triggers a rebuild that drops it
        self.assertEqual(self.packages(), ["six==1.17.0"])
        self.requirements("six==1.17.0", "atom-sync-test-no-such-package==1.0")
        with self.assertRaises(ValueError): self.run_sync()
        self.assertEqual(self.packages(), ["six==1.17.0"])    # failed install: the previous venv is back
        self.assertFalse((self.root / sync.VENV_OLD_DIR).exists())


if __name__ == "__main__":
    unittest.main()
