"""Prevent intermittent CLI failures from option-looking random QA passwords."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


RUNNER = Path(__file__).resolve().parents[2] / "spike" / "tests" / "run_all.py"
spec = importlib.util.spec_from_file_location("regression_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class TestRunnerPassword(unittest.TestCase):
    def test_leading_dash_from_random_source_is_safe_for_argparse(self):
        # This exact random shape broke main's clean checkout after PR #50.
        with patch.object(runner.secrets, "token_urlsafe", return_value="-unlucky"):
            password = runner.qa_cli_password()
        self.assertEqual(password, "qa_-unlucky")
        self.assertTrue(password[0].isalpha())
        self.assertFalse(password.startswith("-"))

    def test_random_secret_is_still_present(self):
        with patch.object(runner.secrets, "token_urlsafe", return_value="abC_123"):
            self.assertEqual(runner.qa_cli_password(), "qa_abC_123")


if __name__ == "__main__":
    unittest.main()
