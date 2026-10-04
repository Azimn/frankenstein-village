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


def _run(args, *, cwd=None, env=None, stdin=None):
    printable = " ".join(str(arg) for arg in args)
    print(f"+ {printable}")
    subprocess.run(
        [str(arg) for arg in args],
        cwd=cwd,
        env=env,
        stdin=stdin,
        check=True,
    )


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

    env = os.environ.copy()
    env["PATH"] = str(_bin("python").parent) + os.pathsep + env.get("PATH", "")

    _run([evennia, "migrate"], cwd=GAME, env=env)
    with (GAME / "world" / "build_spike.py").open("rb") as build_script:
        _run([evennia, "shell"], cwd=GAME, env=env, stdin=build_script)

    print()
    print("Bootstrap complete.")
    print(f"Start: {evennia} start")
    print(f"Game directory: {GAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
