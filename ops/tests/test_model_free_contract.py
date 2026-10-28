"""Guard the default startup and release path against accidental LLM requirements."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops"))
from launch_gate import REQUIRED

MODEL_PACKAGES = (
    "ollama", "openai", "anthropic", "transformers", "torch",
    "llama-cpp", "llama-cpp-python", "langchain", "vllm", "litellm",
    "sentence-transformers",
)
MODEL_ENV = (
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_HOST",
    "MODEL_ENDPOINT", "LLM_API_KEY",
)


def _distribution_name(declaration):
    """Return the normalized PEP 503 name before extras or version constraints."""
    match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", declaration.strip())
    if not match:
        return None
    return re.sub(r"[-_.]+", "-", match.group(1)).lower()


def _core_distributions(path, visited=None):
    """Inspect default requirements and local includes, failing closed on opaque directives."""
    visited = set() if visited is None else visited
    path = path.resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise AssertionError(f"Requirement include escapes repository: {path}")
    if path in visited:
        return []
    visited.add(path)
    packages = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("--requirement="):
            included = line.split("=", 1)[1].strip()
        elif line.startswith("--requirement "):
            included = line.split(maxsplit=1)[1].strip()
        elif line.startswith("-r"):
            included = line[2:].strip()
        else:
            # Editable, remote and pip option directives cannot silently evade
            # the default-install model dependency guard.
            if line.startswith("-") or line.startswith(("git+", "http://", "https://")):
                raise AssertionError(f"Uninspectable core requirement: {line}")
            # A wheel, sdist, egg or local file URL is installable without
            # declaring its true distribution name in the requirement line.
            # Never infer the package identity from an archive filename.
            declaration = line.split(" #", 1)[0].strip()
            if ("file:" in declaration.lower() or re.search(
                r"\.(?:whl|zip|egg|tar(?:\.(?:gz|bz2|xz))?|tgz)(?:[?#].*)?$",
                declaration, re.IGNORECASE,
            )):
                raise AssertionError(f"Uninspectable core archive: {line}")
            name = _distribution_name(declaration)
            if name is None:
                raise AssertionError(f"Invalid core requirement: {line}")
            packages.append(name)
            continue
        if not included or included.startswith(("http://", "https://")):
            raise AssertionError(f"Uninspectable requirement include: {line}")
        packages.extend(_core_distributions(path.parent / included, visited))
    return packages


class ModelFreeContractTests(unittest.TestCase):
    def test_core_install_has_no_llm_dependencies(self):
        packages = _core_distributions(ROOT / "requirements.txt")
        for package in MODEL_PACKAGES:
            self.assertNotIn(package, packages)

    def test_nested_requirements_cannot_hide_model_sdk(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory(dir=ROOT) as temp:
            directory = Path(temp)
            (directory / "nested.txt").write_text(
                "llama_cpp_python[server]>=0.3\n", encoding="utf-8"
            )
            for include in ("-r nested.txt", "-rnested.txt", "--requirement=nested.txt"):
                (directory / "requirements.txt").write_text(
                    include + "\n", encoding="utf-8"
                )
                packages = _core_distributions(directory / "requirements.txt")
                self.assertIn("llama-cpp-python", packages)
                self.assertIn("llama-cpp-python", MODEL_PACKAGES)

    def test_uninspectable_core_requirement_is_not_silently_ignored(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory(dir=ROOT) as temp:
            path = Path(temp) / "requirements.txt"
            for line in ("-e git+https://example.org/model#egg=ollama",
                         "-r https://example.org/requirements.txt",
                         "ollama-0.6.1-py3-none-any.whl",
                         "ollama-0.6.1.tar.gz",
                         "local_model.zip",
                         "ollama @ file:///tmp/ollama.whl"):
                path.write_text(line + "\n", encoding="utf-8")
                with self.subTest(line=line), self.assertRaises(AssertionError):
                    _core_distributions(path)

    def test_nested_local_archive_cannot_hide_model_sdk(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory(dir=ROOT) as temp:
            directory = Path(temp)
            (directory / "nested.txt").write_text(
                "ollama-0.6.1-py3-none-any.whl\n", encoding="utf-8"
            )
            (directory / "requirements.txt").write_text(
                "-r nested.txt\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(AssertionError, "Uninspectable core archive"):
                _core_distributions(directory / "requirements.txt")

    def test_requirement_name_variants_cannot_bypass_model_guard(self):
        for declaration, name in (
            ("openai~=2.0", "openai"),
            ("openai[async]>=2", "openai"),
            ("sentence_transformers==3.0", "sentence-transformers"),
            ("sentence.transformers >= 3", "sentence-transformers"),
            ("llama_cpp_python[server] >= 0.3", "llama-cpp-python"),
            ("transformers @ https://example.org/package.whl", "transformers"),
        ):
            with self.subTest(declaration=declaration):
                self.assertEqual(_distribution_name(declaration), name)

    def test_optional_ai_client_audit_is_not_ordinary_release_gate(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        optional_client = (ROOT / "ops/HEADLESS_AI_CLIENT.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("Do not begin multiplayer soak until the independent AI-first audit clears.", readme)
        self.assertNotIn(
            "independent ai observations are still required before approving the public alpha.",
            " ".join(optional_client.lower().split()),
        )
        self.assertIn("not a model-free release gate", optional_client)

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
            "Frankenstein Village",
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
