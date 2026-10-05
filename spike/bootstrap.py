#!/usr/bin/env python3
"""Create a reproducible local Frankenstein Village spike environment.

The script intentionally does not contain credentials. Evennia's first-run
superuser values must be supplied through the standard environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import venv


ROOT = Path(__file__).resolve().parents[1]
SPIKE = ROOT / "spike"
GAME = SPIKE / "fvillage"
VENV = SPIKE / "venv"
REQUIREMENTS = ROOT / "requirements.txt"
REQUIRED_SUPERUSER_ENV = (
    "EVENNIA_SUPERUSER_USERNAME",
    "EVENNIA_SUPERUSER_EMAIL",
    "EVENNIA_SUPERUSER_PASSWORD",
)


def _bin(name: str) -> Path:
    directory = VENV / ("Scripts" if os.name == "nt" else "bin")
    suffix = ".exe" if os.name == "nt" else ""
    return directory / f"{name}{suffix}"


def _run(args, *, cwd=None, env=None, stdin=None, input_text=None):
    printable = " ".join(str(arg) for arg in args)
    print(f"+ {printable}")
    kwargs = {
        "cwd": cwd,
        "env": env,
        "check": True,
    }
    if input_text is not None:
        kwargs["input"] = input_text
        kwargs["text"] = True
    else:
        kwargs["stdin"] = stdin
    subprocess.run([str(arg) for arg in args], **kwargs)


def _ensure_twistd_launcher(python: Path) -> None:
    """Create the Twisted launcher Evennia expects when pip omits it."""
    bindir = python.parent
    if os.name == "nt":
        exe = bindir / "twistd.exe"
        cmd = bindir / "twistd.cmd"
        if exe.exists() or cmd.exists():
            return
        cmd.write_text(
            f'@"{python}" -c "from twisted.scripts.twistd import run; run()" %*\\n',
            encoding="utf-8",
        )
        print(f"Created Twisted launcher: {cmd}")
        return

    launcher = bindir / "twistd"
    if launcher.exists():
        return
    launcher.write_text(
        f"#!{python}\\nfrom twisted.scripts.twistd import run\\nrun()\\n",
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    print(f"Created Twisted launcher: {launcher}")


def main() -> int:
    if sys.version_info[:2] != (3, 12):
        print(
            "Frankenstein Village is pinned to Python 3.12; "
            f"this interpreter is {sys.version.split()[0]}.",
            file=sys.stderr,
        )
        return 2

    missing = [name for name in REQUIRED_SUPERUSER_ENV if not os.environ.get(name)]
    if missing:
        print(
            "Set these environment variables before bootstrap: "
            + ", ".join(missing),
            file=sys.stderr,
        )
        return 2

    if not VENV.exists():
        print(f"Creating virtual environment: {VENV}")
        venv.EnvBuilder(with_pip=True).create(VENV)

    python = _bin("python")
    evennia = _bin("evennia")
    _run([python, "-m", "pip", "install", "--upgrade", "pip"])
    _run([python, "-m", "pip", "install", "-r", REQUIREMENTS])
    _ensure_twistd_launcher(python)

    env = os.environ.copy()
    env["PATH"] = str(_bin("python").parent) + os.pathsep + env.get("PATH", "")
    (GAME / "server" / "logs").mkdir(parents=True, exist_ok=True)

    _run([evennia, "migrate"], cwd=GAME, env=env)

    # The launcher creates Account #1 from the supplied environment variables
    # before opening the Django shell. Run Evennia's own initial-setup sequence
    # synchronously here so Limbo #2 exists before our world builder runs.
    initial_setup = """
from evennia.server import initial_setup
initial_setup.reset_server = lambda: None
initial_setup.handle_setup(None)
print("INITIAL_SETUP_GREEN")
"""
    _run([evennia, "shell"], cwd=GAME, env=env, input_text=initial_setup)

    with (GAME / "world" / "build_spike.py").open("rb") as build_script:
        _run([evennia, "shell"], cwd=GAME, env=env, stdin=build_script)

    print()
    print("Bootstrap complete.")
    print(f"Start: {evennia} start")
    print(f"Game directory: {GAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
