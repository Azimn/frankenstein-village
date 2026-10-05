#!/usr/bin/env python3
"""Create a reproducible local Frankenstein Village spike environment.

The script intentionally does not contain credentials. Evennia's first-run
superuser values must be supplied through the standard environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
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


def _default_home_exists() -> bool:
    """Return whether Evennia's required default home object (#2) exists."""
    database = GAME / "server" / "evennia.db3"
    if not database.exists():
        return False
    try:
        with sqlite3.connect(database) as conn:
            row = conn.execute(
                "SELECT 1 FROM objects_objectdb WHERE id = 2 LIMIT 1"
            ).fetchone()
        return row is not None
    except sqlite3.Error:
        return False


def _wait_for_default_home(timeout: float = 45.0) -> None:
    """Wait for Evennia's asynchronous first-start setup to create Limbo."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _default_home_exists():
            return
        time.sleep(0.25)
    raise RuntimeError(
        "Evennia started but did not create DEFAULT_HOME (#2) during initial setup."
    )


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

    # Evennia creates account #1, Limbo #2, and its other initial objects on
    # the first start, not during migrate. The world builder needs #2 as its
    # default home, so initialize a genuinely fresh database before building.
    if not _default_home_exists():
        print("Initializing Evennia default database objects...")
        _run([evennia, "start"], cwd=GAME, env=env)
        _wait_for_default_home()
        _run([evennia, "stop"], cwd=GAME, env=env)

    with (GAME / "world" / "build_spike.py").open("rb") as build_script:
        _run([evennia, "shell"], cwd=GAME, env=env, stdin=build_script)

    print()
    print("Bootstrap complete.")
    print(f"Start: {evennia} start")
    print(f"Game directory: {GAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
