"""Guard the default startup and release path against accidental LLM requirements."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops"))
from launch_gate import REQUIRED

MODEL_PACKAGES = (
    "ollama", "openai", "anthropic", "transformers", "torch",
    "llama-cpp", "langchain", "vllm", "litellm", "sentence-transformers",
)
MODEL_ENV = (
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_HOST",
    "MODEL_ENDPOINT", "LLM_API_KEY",
)


class ModelFreeContractTests(unittest.TestCase):
    def test_core_install_has_no_llm_dependencies(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        packages = [
            row.split("==", 1)[0].split(">=", 1)[0].strip().lower()
            for line in requirements.splitlines()
            if (row := line.split("#", 1)[0].strip())
        ]
        for package in MODEL_PACKAGES:
            self.assertNotIn(package, packages)

    def test_startup_and_public_host_do_not_demand_model_credentials(self):
        for path in (
            ROOT / "spike/bootstrap.py",
            ROOT / "spike/fvillage/server/conf/deployment_profile.py",
            ROOT / "spike/fvillage/server/conf/settings.py",
        ):
            source = path.read_text(encoding="utf-8").upper()
            for credential in MODEL_ENV:
                with self.subTest(path=path.name, credential=credential):
                    self.assertNotIn(credential, source)

    def test_login_banner_is_playable_without_agent_tools(self):
        banner = (
            ROOT / "spike/fvillage/server/conf/connection_screens.py"
        ).read_text(encoding="utf-8")
        for phrase in (
            "Victorian Gothic multiplayer text adventure",
            "No language model",
            "create <username> <password>",
            "connect <username> <password>",
            "substrate human",
            "charcreate <name>",
            "Type |wguide|n",
        ):
            self.assertIn(phrase, banner)
        self.assertIn("Automated clients may optionally", banner)

    def test_no_ai_client_or_model_is_part_of_release_manifest(self):
        for forbidden in (
            "ai_external_reconnect", "ai_account_access",
            "independent_model_led_playtest", "llm_test",
        ):
            self.assertNotIn(forbidden, REQUIRED)
        self.assertIn("ordinary_client_reconnect", REQUIRED)
        self.assertIn("ordinary_account_access", REQUIRED)


if __name__ == "__main__":
    unittest.main()
