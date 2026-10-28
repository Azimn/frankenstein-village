#!/usr/bin/env python3
"""Review traceability for Master GDD §19.4 T-01..T-16.

Reads committed issue evidence and validates the named test/fixture anchors in
the current repository. It never upgrades a neighboring test into proof that
the specified GDD negative case actually ran, and never touches game state.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = Path("ops/PHASE_A_GDD_T01_T16_EVIDENCE_2026-10-25.json")


def _test_methods(file: Path) -> set[str]:
    tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            result.add(node.name)
    return result


def validate(root: Path = ROOT, data: dict | None = None) -> dict:
    record = data if data is not None else json.loads((root / REGISTER).read_text(encoding="utf-8"))
    cases = record["cases"]
    expected = ["T-%02d" % i for i in range(1, 17)]
    ids = [case["id"] for case in cases]
    if ids != expected:
        raise ValueError("Master GDD §19.4 requires exact ordered T-01 through T-16")
    if record["full_pass_count"] != 0:
        raise ValueError("Source-only audit cannot assert fully passing end-to-end cases")
    for case in cases:
        if case["assessment"] not in {"partial", "gap"}:
            raise ValueError(case["id"] + ": not a source-only evidence status")
        if (case["exact_gdd_scenario_executed_end_to_end"]
                or case["uncoached_player_verified"]):
            raise ValueError(case["id"] + ": unsupported completion claim")
        if not case.get("open_gap") or not case.get("source_evidence"):
            raise ValueError(case["id"] + ": must disclose gap and test anchor")
        for item in case["source_evidence"]:
            relpath = Path(item["path"])
            if (relpath.is_absolute() or ".." in relpath.parts
                    or not str(relpath).startswith(("ops/tests/", "spike/tests/"))):
                raise ValueError(case["id"] + ": unsafe/out-of-scope source path")
            test_file = root / relpath
            if item["evidence_tier"] == "unit_test_case":
                if item["symbol"] not in _test_methods(test_file):
                    raise ValueError(case["id"] + ": missing actual unit test " + item["symbol"])
            elif item["evidence_tier"] == "existing_scripted_fixture":
                if item["symbol"] not in test_file.read_text(encoding="utf-8"):
                    raise ValueError(case["id"] + ": missing actual scripted fixture " + item["symbol"])
            else:
                raise ValueError(case["id"] + ": unknown source-evidence tier")
    return record


def markdown(data: dict) -> str:
    out = [
        "# Master GDD §19.4: Negative-case execution gap register",
        "",
        "**Assessment basis:** source inspection only, not scenario-level CI.",
        "An existing unit test or scripted fixture does not satisfy the GDD",
        "scenario merely because it touches a nearby subsystem.",
        "",
        "| ID | Required negative case | Existing adjacent evidence | Unverified proof |",
        "| --- | --- | --- | --- |",
    ]
    for case in data["cases"]:
        test_names = ", ".join(
            src["path"] + ":" + src["symbol"]
            for src in case["source_evidence"]
        )
        out.append(
            "| " + case["id"] + " | " + case["scenario"] +
            " | " + test_names.replace("|", "/") + " | " +
            case["open_gap"].replace("|", "/") + " |"
        )
    out += [
        "", "## Execution priorities",
        "",
        "1. T-07 Hound versus Wanderer is the clearest unique-role mechanics gap.",
        "   Reuse route/survey and real environmental hazards; prove a distinct",
        "   field judgment through two ordinary accounts before claiming parity.",
        "2. T-08 patient consent and T-09 bodily-relief exhaustion require",
        "   explicit privacy and alternate-relief mechanics, not inference",
        "   from finite clinic and food stock tests.",
        "3. T-13 cancellation/completion races and T-02 last-item contention",
        "   need transactional two-account tests with exactly-once custody.",
        "4. Revisit T-01, T-03–T-06, T-10–T-12, T-14–T-16 with the",
        "   GDD's exact negative preconditions and real process restart.",
        "",
        "Only promote a row after exact-head executed scenario evidence, clear",
        "world state, accurate witness/privacy and restart checks are attached.",
        "Uncoached quality remains an independent requirement.",
    ]
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    data = validate()
    print(json.dumps(data, indent=2, sort_keys=True) if args.format == "json"
          else markdown(data), end="\n")


if __name__ == "__main__":
    main()
