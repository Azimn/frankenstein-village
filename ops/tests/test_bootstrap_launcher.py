"""Validate fallback launcher bytes without installing Evennia or Twisted."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest


BOOTSTRAP = Path(__file__).resolve().parents[2] / "spike" / "bootstrap.py"
spec = importlib.util.spec_from_file_location("fvillage_bootstrap", BOOTSTRAP)
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


class LauncherTests(unittest.TestCase):
    def test_windows_fallback_is_a_real_batch_line(self):
        script = bootstrap._twistd_launcher_text(
            Path("C:/games/fvillage/venv/Scripts/python.exe"), windows=True
        )
        self.assertTrue(script.startswith('@"C:'))
        self.assertIn("from twisted.scripts.twistd import run; run()", script)
        self.assertTrue(script.endswith("\n"))
        self.assertNotIn("\\n", script)

    def test_unix_fallback_is_three_real_executable_lines(self):
        with tempfile.TemporaryDirectory() as temp:
            python = Path(temp) / "python"
            expected = (
                f"#!{python}\n"
                "from twisted.scripts.twistd import run\n"
                "run()\n"
            )
            self.assertEqual(
                bootstrap._twistd_launcher_text(python, windows=False),
                expected,
            )
            self.assertNotIn("\\n", expected)
            if os.name != "posix":
                return
            bootstrap._ensure_twistd_launcher(python)
            launcher = python.parent / "twistd"
            self.assertEqual(launcher.read_text(encoding="utf-8"), expected)
            self.assertTrue(launcher.stat().st_mode & stat.S_IXUSR)
            # Existing, installed launchers are not overwritten by bootstrap.
            launcher.write_text("already-installed\n", encoding="utf-8")
            bootstrap._ensure_twistd_launcher(python)
            self.assertEqual(
                launcher.read_text(encoding="utf-8"), "already-installed\n"
            )


if __name__ == "__main__":
    unittest.main()
