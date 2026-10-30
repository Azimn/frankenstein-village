#!/usr/bin/env python3
"""One-command Frankenstein Village clean-checkout regression runner."""

from __future__ import annotations

import os
import json
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


def qa_cli_password() -> str:
    """Argparse-safe random test credential, never an option-looking token.

    secrets.token_urlsafe() may begin with '-' and would then be parsed as a
    flag after --password; prefix an ASCII letter for deterministic syntax.
    """
    return "qa_" + secrets.token_urlsafe(24)


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



def stop_evennia_after_phase(evennia: Path, *, game: Path, env: dict,
                             phase_failed: bool) -> None:
    """Keep the original gameplay failure if server cleanup also fails.

    A failed stop on an otherwise successful phase is still a test failure.
    This helper never reports a green phase after either failure.
    """
    try:
        run([evennia, "stop"], cwd=game, env=env, timeout=60)
    except Exception as stop_error:
        if not phase_failed:
            raise
        print(
            f"Evennia stop also failed; original gameplay failure retained: "
            f"{stop_error}",
            file=sys.stderr,
        )


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
        password = qa_cli_password()
        env = os.environ.copy()
        env.update(
            {
                "EVENNIA_SUPERUSER_USERNAME": username,
                "EVENNIA_SUPERUSER_EMAIL": "qa-admin@example.invalid",
                "EVENNIA_SUPERUSER_PASSWORD": password,
                "FV_QA_REPAIR_PASSWORD": secrets.token_urlsafe(24),
                "PYTHONUNBUFFERED": "1",
            }
        )

        game = checkout / "spike" / "fvillage"
        try:
            run(
                [
                    sys.executable, "-m", "unittest", "discover",
                    "-s", "ops/tests", "-p", "test_*.py", "-v",
                ],
                cwd=checkout,
                env=env,
            )
            print("OPS_BACKUP_RESTORE_GREEN")
            run(
                [sys.executable, "spike/tests/resident_population_sim.py"],
                cwd=checkout,
                env=env,
            )
            run(
                [sys.executable, "spike/tests/commons_sim.py"],
                cwd=checkout,
                env=env,
            )
            run(
                [sys.executable, "spike/tests/commons_follow_sim.py"],
                cwd=checkout,
                env=env,
            )
            run(
                [sys.executable, "spike/tests/community_hearth_sim.py"],
                cwd=checkout,
                env=env,
            )
            run(
                [sys.executable, "spike/tests/resident_hearth_sim.py"],
                cwd=checkout,
                env=env,
            )
            run(
                [sys.executable, "spike/tests/resident_environment_sim.py"],
                cwd=checkout,
                env=env,
            )
            run(
                [sys.executable, "spike/tests/resident_life_sim.py"],
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
                # Mutate the registered physical growth, never a same-name
                # legacy decoy selected by an arbitrary global search order.
                "from world.object_properties import configure_mechanical_properties\n"
                "from commands.village_cmds import _preferred_well_growth_pickup\n"
                "square = [o for o in search.search_object('Village Square') if o.key == 'Village Square'][0]\n"
                "shroom = _preferred_well_growth_pickup([o for o in square.contents if o.key == 'a cluster of mushrooms'], square)\n"
                "assert shroom is not None, 'registered growth missing before rebuild'\n"
                "well = [o for o in square.contents if o.key == 'well' and o.is_typeclass('typeclasses.objects.VillageWell', exact=True)][0]\n"
                "well.db.qa_expected_growth_id = shroom.id\n"
                "configure_mechanical_properties(shroom, {}, hidden_properties={})\n"
                "shroom.db.desc = 'stale mushroom description'\n"
                "shroom.db.consume = {'toxic': 25, 'nourish': 5}\n"
                "shroom.aliases.remove('toadstools')\n"
                "shroom.tags.remove('food')\n"
                "print('IDEMPOTENCE_SENTINELS_SET')\n"
            )
            run([evennia, "shell"], cwd=game, env=env, input_text=mutate)

            build = (game / "world" / "build_spike.py").read_text(encoding="utf-8")
            run([evennia, "shell"], cwd=game, env=env, input_text=build)

            # Rebuilding the world must restore the SAME registered specimen
            # without creating a duplicate or losing its physical identity.
            rebuild_proof = (
                "from evennia.utils import search\n"
                "from commands.village_cmds import ensure_well_mushrooms\n"
                "from world.object_properties import hidden_mechanical_properties\n"
                "well = [o for o in search.search_object('village well') if o.key == 'well' and o.is_typeclass('typeclasses.objects.VillageWell', exact=True)][0]\n"
                "before = tuple(well.db.well_mushroom_spawn_ids or [])\n"
                "grown = ensure_well_mushrooms()\n"
                "assert grown is not None and grown.id == well.db.qa_expected_growth_id\n"
                "assert tuple(well.db.well_mushroom_spawn_ids or []) == before\n"
                "assert hidden_mechanical_properties(grown) == {'toxin': 25}\n"
                "print('WELL_CANONICAL_REBUILD_IDEMPOTENT_GREEN')\n"
            )
            run([evennia, "shell"], cwd=game, env=env, input_text=rebuild_proof)

            assertions = (checkout / "spike" / "tests" / "world_assertions.py").read_text(
                encoding="utf-8"
            )
            run([evennia, "shell"], cwd=game, env=env, input_text=assertions)

            # Controlled pre-telnet cold exposure: initialize AFTER the
            # broad world simulation so its time-jump tests cannot decay the
            # observation stimulus before a real player tends the fire.
            hearth_witness_seed = (
                "from evennia.utils import search\n"
                "from world.residents import resident_state, save_state\n"
                "for key in ('Mara Crowe', 'Marta Kovács'):\n"
                "    resident = [o for o in search.search_object(key) if o.key == key][0]\n"
                "    state = resident_state(resident)\n"
                "    state['life']['body']['cold'] = 78.0\n"
                "    save_state(resident, state)\n"
                "print('HEARTH_WITNESS_COLD_SENTINELS_SET')\n"
            )
            run(
                [evennia, "shell"], cwd=game, env=env,
                input_text=hearth_witness_seed,
            )

            # Seed two distinct QA accounts before live telnet. Creating accounts
            # through the public socket is rate-limited by design and the two
            # other QA accounts already have active masks during this scenario.
            # This fixture changes no server anti-abuse or mask-isolation rule.
            repair_accounts = (
                "import os\n"
                "from evennia.utils import create\n"
                "from evennia.accounts.models import AccountDB\n"
                "for key in ('qa_smith_repair', 'qa_merchant_repair', 'qa_mystic_study', 'qa_performer_stage', 'qa_wanderer_mail', 'qa_hound_protection', 'qa_detective_clinic'):\n"
                "    account = AccountDB.objects.filter(db_key=key).first()\n"
                "    if account is None:\n"
                "        account = create.create_account(\n"
                "            key, email=key + '@example.invalid',\n"
                "            password=os.environ['FV_QA_REPAIR_PASSWORD']\n"
                "        )\n"
                "    account.db.substrate = 'ai'\n"
                "    account.db.disclosure_consent = True\n"
                "print('REPAIR_QA_ACCOUNTS_READY')\n"
            )
            run([evennia, "shell"], cwd=game, env=env, input_text=repair_accounts)

            # Set only the disposable QA world to a rare Mystic study night.
            # This does not alter production scheduling or add a privileged
            # player verb. The test then performs every action via telnet.
            mystic_night_fixture = (
                "from evennia.scripts.models import ScriptDB\n"
                "from evennia.utils import search\n"
                "from world.residents import advance_population\n"
                "from world.mystic_circles import manifested\n"
                "clock = ScriptDB.objects.get(db_key='village_time')\n"
                "assert int(clock.db.day or 1) == 1, 'fresh QA world must start on day one'\n"
                "clock.db.hour = 21\n"
                "advance_population(day=1, hour=21, emit=False)\n"
                "graveyard = [r for r in search.search_object('St. Lazarus Churchyard') "
                "if r.key == 'St. Lazarus Churchyard'][0]\n"
                "names = {o.key for o in graveyard.contents}\n"
                "assert {'Beatrice Harcourt', 'Mirela Dobre'} <= names, names\n"
                "assert manifested(1, 21)\n"
                "print('MYSTIC_NIGHT_QA_READY')\n"
            )
            run([evennia, "shell"], cwd=game, env=env, input_text=mystic_night_fixture)

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
                    # Multiple real players and the four-landmark field
                    # investigation exceed the former 180s on CI runners.
                    # The workflow retains a strict 20-minute global cap.
                    timeout=480,
                )

                # Real autonomous-client validation, not a fake socket peer:
                # both QA accounts are independently authenticated, have
                # declared the AI substrate, and use ordinary player verbs.
                # The client must discover all ten reachable IC rooms from
                # permission-checked local exits and return to the Tavern.
                bot_file = Path(tmp) / "qa-agent-accounts.json"
                bot_file.write_text(json.dumps([
                    {"username": "qa_smith_repair",
                     "character": "SmithTester",
                     "password_env": "FV_QA_REPAIR_PASSWORD"},
                    {"username": "qa_merchant_repair",
                     "character": "MerchantTester",
                     "password_env": "FV_QA_REPAIR_PASSWORD"},
                ]), encoding="utf-8")
                bot_result = Path(tmp) / "real-agent-exploration.json"
                run(
                    [
                        vpython, checkout / "ops" / "headless_ai_client.py",
                        "--host", "127.0.0.1", "--port", "4000",
                        "--accounts", bot_file, "--sessions", "2",
                        "--steps", "1", "--explore-rooms", "11",
                        "--timeout", "8", "--seed", "41016",
                        "--output", bot_result,
                    ],
                    cwd=checkout, env=env, timeout=200,
                )
                proof = json.loads(bot_result.read_text(encoding="utf-8"))
                assert proof["passed"] and proof["session_count"] == 2
                for agent in proof["results"]:
                    assert agent["error"] is None, agent
                    assert agent["exploration"]["target"] == 11, agent
                    assert agent["exploration"]["visited_count"] == 11, agent
                    assert agent["exploration"]["returned_to_start"], agent
                    assert agent["connect_success"] and agent["commands"] > 20
                print("REAL_TWO_AGENT_VILLAGE_EXPLORATION_GREEN")

                # A separate REAL concurrent held-TCP-connection smoke verifies
                # the new duration instrument on the unprivileged QA accounts.
                # Its 8-second window explicitly cannot meet the 30-minute
                # operator soak gate or claim public launch readiness.
                held_out = Path(tmp) / "continuous-players-smoke.json"
                run(
                    [
                        vpython,
                        checkout / "ops" / "continuous_player_soak.py",
                        "--host", "127.0.0.1", "--port", "4000",
                        "--accounts", bot_file, "--sessions", "2",
                        "--smoke-seconds", "8",
                        "--interval-seconds", "2",
                        "--timeout", "8", "--output", held_out,
                    ],
                    cwd=checkout, env=env, timeout=100,
                )
                held = json.loads(held_out.read_text(encoding="utf-8"))
                assert held["sessions_attempted"] == 2
                assert held["sessions_passed"] == 2
                assert held["passed_short_smoke"] is True
                assert held["technical_thresholds_met"] is False
                assert held["public_launch_certified"] is False
                assert held["shortest_held_seconds"] >= 8
                assert held["lost_connections"] == 0
                print("REAL_TWO_PLAYER_HELD_CONNECTION_SMOKE_GREEN")
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

            # Seed a hostile same-name legacy decoy only AFTER ordinary-client
            # health/inquiry play, so those existing scenarios remain intact.
            # This persists through the real process restart below and checks
            # that a copied source ID and hidden toxin never become registry proof.
            migrated_well_fixture = (
                "from evennia.utils import search, create\n"
                "from commands.village_cmds import ensure_well_mushrooms, _preferred_well_growth_pickup\n"
                "from world import clinic_inquiry_state\n"
                "from world.object_properties import configure_mechanical_properties\n"
                "square = [o for o in search.search_object('Village Square') if o.key == 'Village Square'][0]\n"
                "well = [o for o in square.contents if o.key == 'well' and o.is_typeclass('typeclasses.objects.VillageWell', exact=True)][0]\n"
                "legacy = create.create_object('typeclasses.objects.Object', key='a cluster of mushrooms', location=square, aliases=['mushrooms', 'cluster', 'toadstools'])\n"
                "legacy.db.qa_legacy_mushroom_decoy = True\n"
                "legacy.db.well_mushroom_source_id = well.id\n"
                "configure_mechanical_properties(legacy, {}, hidden_properties={'toxin': 25})\n"
                "grown = ensure_well_mushrooms()\n"
                "assert grown is not None and grown.id != legacy.id\n"
                "before = list(well.db.well_mushroom_spawn_ids or [])\n"
                "assert not clinic_inquiry_state.registered_well_growth(legacy.id, before)\n"
                "assert clinic_inquiry_state.registered_well_growth(grown.id, before)\n"
                "assert _preferred_well_growth_pickup([legacy, grown], square) is grown\n"
                "assert ensure_well_mushrooms().id == grown.id\n"
                "assert list(well.db.well_mushroom_spawn_ids or []) == before\n"
                "print('WELL_MIGRATED_LEGACY_COEXISTENCE_PRE_RESTART_GREEN')\n"
            )
            run([evennia, "shell"], cwd=game, env=env,
                input_text=migrated_well_fixture)

            # After the hostile decoy is seeded, use actual authenticated
            # Healer and Detective sockets BEFORE restart. The Healer's
            # ordinary unnumbered get must pick registered growth, not the
            # same-name decoy. The shell below checks exact physical custody.
            run([evennia, "start"], cwd=game, env=env, timeout=120)
            try:
                wait_for_port("127.0.0.1", 4000)
                run(
                    [vpython, checkout / "spike" / "tests" /
                     "telnet_edge28_migrated_restart.py",
                     "--host", "127.0.0.1", "--port", "4000",
                     "--phase", "before"],
                    cwd=checkout, env=env, timeout=100,
                )
            finally:
                stop_evennia_after_phase(
                    evennia, game=game, env=env,
                    phase_failed=sys.exc_info()[0] is not None,
                )

            migrated_player_proof = (
                "from evennia.utils import search\n"
                "from world import clinic_inquiry_state as rules\n"
                "square = [o for o in search.search_object('Village Square') if o.key == 'Village Square'][0]\n"
                "well = [o for o in square.contents if o.key == 'well' and o.is_typeclass('typeclasses.objects.VillageWell', exact=True)][0]\n"
                "healer = [o for o in search.search_object('HealerTester') if o.key == 'HealerTester'][0]\n"
                "ids = rules.well_growth_ids(well.db.well_mushroom_spawn_ids)\n"
                "carried = [o for o in healer.contents if o.key == 'a cluster of mushrooms' and rules.registered_well_growth(o.id, ids)]\n"
                "legacy = [o for o in square.contents if getattr(o.db, 'qa_legacy_mushroom_decoy', False) is True]\n"
                "assert len(carried) == len(legacy) == 1, 'ordinary client picked legacy or lost genuine growth'\n"
                "assert carried[0].db.well_mushroom_source_id == well.id\n"
                "assert legacy[0].id not in ids\n"
                "well.db.qa_migrated_held_id = carried[0].id\n"
                "print('WELL_MIGRATED_AUTHENTICATED_PLAYER_CUSTODY_PRE_RESTART_GREEN')\n"
            )
            run([evennia, "shell"], cwd=game, env=env,
                input_text=migrated_player_proof)

            # Restart the real server process and reconnect BOTH original
            # accounts. Check signed readback, role/privacy denials and
            # ordinary physical drop/get with the persisted legacy decoy.
            try:
                run([evennia, "start"], cwd=game, env=env, timeout=120)
                wait_for_port("127.0.0.1", 4000)
                run(
                    [vpython, checkout / "spike" / "tests" /
                     "telnet_edge28_migrated_restart.py",
                     "--host", "127.0.0.1", "--port", "4000",
                     "--phase", "after"],
                    cwd=checkout, env=env, timeout=100,
                )
                # The telnet after-phase intentionally leaves the newly re-picked
                # item IN the Healer's inventory. Stop Evennia and verify physical
                # exact-ID custody before allowing any final ordinary-client drop.
                # A name-only inventory response plus a final Square location
                # cannot distinguish authentic growth from a forged decoy.
            finally:
                stop_evennia_after_phase(
                    evennia, game=game, env=env,
                    phase_failed=sys.exc_info()[0] is not None,
                )
            migrated_repick_proof = (
                "from evennia.utils import search\n"
                "from world import clinic_inquiry_state as rules\n"
                "square = [o for o in search.search_object('Village Square') if o.key == 'Village Square'][0]\n"
                "well = [o for o in square.contents if o.key == 'well' and o.is_typeclass('typeclasses.objects.VillageWell', exact=True)][0]\n"
                "healer = [o for o in search.search_object('HealerTester') if o.key == 'HealerTester'][0]\n"
                "held_id = well.db.qa_migrated_held_id\n"
                "ids = rules.well_growth_ids(well.db.well_mushroom_spawn_ids)\n"
                "held = [o for o in healer.contents if o.id == held_id and rules.registered_well_growth(o.id, ids)]\n"
                "decoys = [o for o in square.contents if getattr(o.db, 'qa_legacy_mushroom_decoy', False) is True]\n"
                "assert len(held) == len(decoys) == 1, 'post-restart re-pick must hold the original registered specimen, not a decoy'\n"
                "assert held[0].db.well_mushroom_source_id == well.id\n"
                "assert decoys[0].id not in ids and decoys[0].id != held_id\n"
                "assert not [o for o in healer.contents if getattr(o.db, 'qa_legacy_mushroom_decoy', False) is True], 'forged decoy entered player custody'\n"
                "assert not [o for o in square.contents if o.id == held_id], 'original growth remained on Square after re-pick'\n"
                "print('WELL_MIGRATED_AUTHENTICATED_REPICK_EXACT_ID_POST_RESTART_GREEN')\n"
            )
            run([evennia, "shell"], cwd=game, env=env,
                input_text=migrated_repick_proof)
            # Reconnect the same ordinary Healer after the independent
            # stopped-server oracle, release the original item onto Square,
            # and retain the existing final Square/decoy negative assertion.
            try:
                run([evennia, "start"], cwd=game, env=env, timeout=120)
                wait_for_port("127.0.0.1", 4000)
                run(
                    [vpython, checkout / "spike" / "tests" /
                     "telnet_edge28_migrated_restart.py",
                     "--host", "127.0.0.1", "--port", "4000",
                     "--phase", "release"],
                    cwd=checkout, env=env, timeout=100,
                )
                # GDD T-03: retry the already completed physical lamp repair through
                # the original Smith's authenticated client after a real restart.
                # A read-only post-restart shell then verifies the objective record.
                run(
                    [
                        vpython,
                        checkout / "spike" / "tests" / "telnet_t03_restart_retry.py",
                        "--host", "127.0.0.1", "--port", "4000",
                    ],
                    cwd=checkout, env=env, timeout=90,
                )
            finally:
                stop_evennia_after_phase(
                    evennia, game=game, env=env,
                    phase_failed=sys.exc_info()[0] is not None,
                )
            migrated_post_client_proof = (
                "from evennia.utils import search\n"
                "from world import clinic_inquiry_state as rules\n"
                "square = [o for o in search.search_object('Village Square') if o.key == 'Village Square'][0]\n"
                "well = [o for o in square.contents if o.key == 'well' and o.is_typeclass('typeclasses.objects.VillageWell', exact=True)][0]\n"
                "healer = [o for o in search.search_object('HealerTester') if o.key == 'HealerTester'][0]\n"
                "held_id = well.db.qa_migrated_held_id\n"
                "ids = rules.well_growth_ids(well.db.well_mushroom_spawn_ids)\n"
                "growth = [o for o in square.contents if o.id == held_id and rules.registered_well_growth(o.id, ids)]\n"
                "legacy = [o for o in square.contents if getattr(o.db, 'qa_legacy_mushroom_decoy', False) is True]\n"
                "assert len(growth) == len(legacy) == 1 and legacy[0].id not in ids\n"
                "assert growth[0].db.well_mushroom_source_id == well.id\n"
                "assert not [o for o in healer.contents if o.id == held_id]\n"
                "print('WELL_MIGRATED_AUTHENTICATED_PLAYER_CUSTODY_POST_RESTART_GREEN')\n"
            )
            run([evennia, "shell"], cwd=game, env=env,
                input_text=migrated_post_client_proof)
            post_restart = (
                checkout / "spike" / "tests" / "post_restart_assertions.py"
            ).read_text(encoding="utf-8")
            run(
                [evennia, "shell"],
                cwd=game,
                env=env,
                input_text=post_restart,
            )
            # GDD T-13: prepare day two while the server is stopped, then
            # perform every state-changing action with two authenticated
            # ordinary telnet accounts. Offline masks cannot sign events.
            t13_setup = (
                checkout / "spike" / "tests" / "gdd_t13_cancel_setup.py"
            ).read_text(encoding="utf-8")
            run([evennia, "shell"], cwd=game, env=env, input_text=t13_setup)
            run([evennia, "start"], cwd=game, env=env, timeout=120)
            try:
                wait_for_port("127.0.0.1", 4000)
                run(
                    [
                        vpython,
                        checkout / "spike" / "tests" / "telnet_t13_cancel.py",
                        "--host", "127.0.0.1", "--port", "4000",
                    ],
                    cwd=checkout, env=env, timeout=140,
                )
            finally:
                run([evennia, "stop"], cwd=game, env=env, timeout=60)
            t13_cancel = (
                checkout / "spike" / "tests" / "gdd_t13_cancel_world_assertions.py"
            ).read_text(encoding="utf-8")
            run([evennia, "shell"], cwd=game, env=env, input_text=t13_cancel)

            # GDD T-12: the same disposable QA database, now after a genuine
            # server restart and with no connected players, must resolve a
            # scheduled blackout by expiry without inventing player help.
            unattended = (
                checkout / "spike" / "tests" / "unattended_blackout_assertions.py"
            ).read_text(encoding="utf-8")
            run(
                [evennia, "shell"],
                cwd=game,
                env=env,
                input_text=unattended,
            )
            # Verify that unattended resolution, history and event-ledger
            # receipts survive a SECOND real Evennia server process restart.
            run([evennia, "start"], cwd=game, env=env, timeout=120)
            wait_for_port("127.0.0.1", 4000)
            run([evennia, "stop"], cwd=game, env=env, timeout=60)
            persisted_blackout = (
                checkout / "spike" / "tests"
                / "unattended_blackout_restart_assertions.py"
            ).read_text(encoding="utf-8")
            run(
                [evennia, "shell"],
                cwd=game,
                env=env,
                input_text=persisted_blackout,
            )
            # T-13's signed cancellation, physical recovery and finite rack
            # must persist through the same real second server restart.
            t13_restart = (
                checkout / "spike" / "tests" / "gdd_t13_cancel_restart_assertions.py"
            ).read_text(encoding="utf-8")
            run([evennia, "shell"], cwd=game, env=env, input_text=t13_restart)

            # T-13: independently exercise a live two-socket cancel/deliver
            # contest, then verify physical custody and signed outcome before
            # and after a THIRD real Evennia process restart. The socket send
            # barrier does not assert parallel server-side execution.
            race_setup = (
                checkout / "spike" / "tests" / "gdd_t13_race_setup.py"
            ).read_text(encoding="utf-8")
            run([evennia, "shell"], cwd=game, env=env, input_text=race_setup)
            run([evennia, "start"], cwd=game, env=env, timeout=120)
            try:
                wait_for_port("127.0.0.1", 4000)
                run(
                    [vpython, checkout / "spike" / "tests" / "telnet_t13_race.py",
                     "--host", "127.0.0.1", "--port", "4000"],
                    cwd=checkout, env=env, timeout=140,
                )
            finally:
                run([evennia, "stop"], cwd=game, env=env, timeout=60)
            race_assertions = (
                checkout / "spike" / "tests" / "gdd_t13_race_assertions.py"
            ).read_text(encoding="utf-8")
            run([evennia, "shell"], cwd=game, env=env,
                input_text=race_assertions)
            run([evennia, "start"], cwd=game, env=env, timeout=120)
            wait_for_port("127.0.0.1", 4000)
            run([evennia, "stop"], cwd=game, env=env, timeout=60)
            restarted_env = dict(env)
            restarted_env["FV_T13_RACE_RESTART"] = "1"
            run([evennia, "shell"], cwd=game, env=restarted_env,
                input_text=race_assertions)

            # T-13: the previous contested outcome must not strand the next
            # day's commission. Advance only the disposable QA clock, then
            # exercise a fresh pledge and cancellation through normal telnet.
            day4_setup = (
                checkout / "spike" / "tests" / "gdd_t13_day4_setup.py"
            ).read_text(encoding="utf-8")
            run([evennia, "shell"], cwd=game, env=env,
                input_text=day4_setup)
            run([evennia, "start"], cwd=game, env=env, timeout=120)
            try:
                wait_for_port("127.0.0.1", 4000)
                run(
                    [vpython, checkout / "spike" / "tests" /
                     "telnet_t13_day4_recovery.py",
                     "--host", "127.0.0.1", "--port", "4000"],
                    cwd=checkout, env=env, timeout=100,
                )
            finally:
                run([evennia, "stop"], cwd=game, env=env, timeout=60)
            day4_assertions = (
                checkout / "spike" / "tests" / "gdd_t13_day4_assertions.py"
            ).read_text(encoding="utf-8")
            run([evennia, "shell"], cwd=game, env=env,
                input_text=day4_assertions)
            run([evennia, "start"], cwd=game, env=env, timeout=120)
            wait_for_port("127.0.0.1", 4000)
            run([evennia, "stop"], cwd=game, env=env, timeout=60)
            day4_restart_env = dict(env)
            day4_restart_env["FV_T13_DAY4_RESTART"] = "1"
            run([evennia, "shell"], cwd=game, env=day4_restart_env,
                input_text=day4_assertions)
        except Exception:
            dump_logs(game)
            raise

    print("\nALL FRANKENSTEIN VILLAGE REGRESSIONS GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
