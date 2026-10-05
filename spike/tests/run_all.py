#!/usr/bin/env python3
"""One-command Frankenstein Village clean-checkout regression runner."""

from __future__ import annotations

import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time


REPO_ROOT = Path(__file__).resolve().parents[2]


def run(args, *, cwd, env, input_text=None, timeout=900):
    printable = " ".join(str(arg) for arg in args)
    print(f"\n$ {printable}")
    proc = subprocess.run(
        [str(arg) for arg in args],
        cwd=cwd,
        env=env,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    if proc.stdout:
        print(proc.stdout)
    if proc.returncode:
        raise RuntimeError(f"command failed with exit code {proc.returncode}: {printable}")
    return proc


def venv_bin(root: Path, name: str) -> Path:
    bindir = root / "spike" / "venv" / ("Scripts" if os.name == "nt" else "bin")
    suffix = ".exe" if os.name == "nt" else ""
    return bindir / f"{name}{suffix}"


def wait_for_port(host: str, port: int, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError(f"server did not open {host}:{port} within {timeout:.0f}s")


def dump_logs(game: Path) -> None:
    logdir = game / "server" / "logs"
    if not logdir.exists():
        return
    for path in sorted(logdir.glob("*")):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if content.strip():
            print(f"\n--- {path.name} (tail) ---")
            print("\n".join(content.splitlines()[-160:]))


def main() -> int:
    if sys.version_info[:2] != (3, 12):
        print(
            f"Regression suite requires Python 3.12; got {sys.version.split()[0]}.",
            file=sys.stderr,
        )
        return 2

    with tempfile.TemporaryDirectory(prefix="fvillage-regression-") as tmp:
        checkout = Path(tmp) / "checkout"
        shutil.copytree(
            REPO_ROOT,
            checkout,
            ignore=shutil.ignore_patterns(
                ".git", "venv", "__pycache__", ".pytest_cache", "*.pyc", "*.pyo"
            ),
        )

        server_dir = checkout / "spike" / "fvillage" / "server"
        for db in server_dir.glob("evennia.db3*"):
            db.unlink()

        username = "qa_admin"
        password = secrets.token_urlsafe(24)
        env = os.environ.copy()
        env.update(
            {
                "EVENNIA_SUPERUSER_USERNAME": username,
                "EVENNIA_SUPERUSER_EMAIL": "qa-admin@example.invalid",
                "EVENNIA_SUPERUSER_PASSWORD": password,
                "PYTHONUNBUFFERED": "1",
            }
        )

        game = checkout / "spike" / "fvillage"
        try:
            run(
                [sys.executable, "spike/tests/resident_population_sim.py"],
                cwd=checkout,
                env=env,
            )
            run([sys.executable, "spike/bootstrap.py"], cwd=checkout, env=env)

            evennia = venv_bin(checkout, "evennia")
            vpython = venv_bin(checkout, "python")
            env["PATH"] = str(evennia.parent) + os.pathsep + env.get("PATH", "")

            mutate = (
                "from evennia.utils import search\n"
                "from world.residents import assign_fact, set_location_availability\n"
                "bram = [o for o in search.search_object('Bram') if o.key == 'Bram'][0]\n"
                "bread = [o for o in search.search_object('a loaf of bread') "
                "if o.key == 'a loaf of bread'][0]\n"
                "lark = [o for o in search.search_object('Lark Vessey') if o.key == 'Lark Vessey'][0]\n"
                "bram.db.till_kr = 37\n"
                "bread.db.servings = 2\n"
                "fact = assign_fact(lark, class_hint='ordinary')\n"
                "lark.db.qa_fact_id = fact['fact_id']\n"
                "set_location_availability('schoolhouse', False, reason='school_destroyed')\n"
                "print('IDEMPOTENCE_SENTINELS_SET')\n"
            )
            run([evennia, "shell"], cwd=game, env=env, input_text=mutate)

            build = (game / "world" / "build_spike.py").read_text(encoding="utf-8")
            run([evennia, "shell"], cwd=game, env=env, input_text=build)

            assertions = (checkout / "spike" / "tests" / "world_assertions.py").read_text(
                encoding="utf-8"
            )
            run([evennia, "shell"], cwd=game, env=env, input_text=assertions)

            started = False
            try:
                run([evennia, "start"], cwd=game, env=env, timeout=120)
                started = True
                wait_for_port("127.0.0.1", 4000)
                run(
                    [
                        vpython,
                        checkout / "spike" / "tests" / "telnet_playthrough.py",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "4000",
                        "--username",
                        username,
                        "--password",
                        password,
                    ],
                    cwd=checkout,
                    env=env,
                    timeout=180,
                )
            finally:
                if started:
                    subprocess.run(
                        [str(evennia), "stop"],
                        cwd=game,
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=60,
                    )

            # Restart the actual server once after player-created resident state
            # exists, then inspect the database through a fresh process.
            run([evennia, "start"], cwd=game, env=env, timeout=120)
            wait_for_port("127.0.0.1", 4000)
            run([evennia, "stop"], cwd=game, env=env, timeout=60)
            post_restart = (
                checkout / "spike" / "tests" / "post_restart_assertions.py"
            ).read_text(encoding="utf-8")
            run(
                [evennia, "shell"],
                cwd=game,
                env=env,
                input_text=post_restart,
            )
        except Exception:
            dump_logs(game)
            raise

    print("\nALL FRANKENSTEIN VILLAGE REGRESSIONS GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
