"""Source-verified, pinned real-client/restart receipts for FV-G01.

No network requests or server activity: recorded CI status is independently
checked during the engineering run. This validates the evidence references
against the test source and never treats partial CI as a completed GDD edge.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = Path("ops/GDD_G01_CI_OBSERVATIONS_2026-10-27.json")


def _static_truth(node: ast.AST) -> bool | None:
    """Evaluate only trivially constant boolean guards, never arbitrary code."""
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        value = _static_truth(node.operand)
        return None if value is None else not value
    return None


class _ReachableCallCollector(ast.NodeVisitor):
    """Collect possible executed AST calls, excluding constant-dead branches.

    This intentionally does not pretend to prove every dynamic branch ran.
    Actual execution proof comes from the pinned, successful CI transcript.
    """
    def __init__(self) -> None:
        self.calls: list[ast.Call] = []

    def visit_Call(self, node: ast.Call) -> None:
        self.calls.append(node)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)
        decision = _static_truth(node.test)
        branches = (node.body if decision is True else
                    node.orelse if decision is False else
                    node.body + node.orelse)
        for stmt in branches:
            self.visit(stmt)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.visit(node.test)
        decision = _static_truth(node.test)
        if decision is True:
            self.visit(node.body)
        elif decision is False:
            self.visit(node.orelse)
        else:
            self.visit(node.body)
            self.visit(node.orelse)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        for value in node.values:
            self.visit(value)
            decision = _static_truth(value)
            if isinstance(node.op, ast.And) and decision is False:
                break
            if isinstance(node.op, ast.Or) and decision is True:
                break

    def visit_While(self, node: ast.While) -> None:
        self.visit(node.test)
        decision = _static_truth(node.test)
        if decision is not False:
            for stmt in node.body:
                self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)


def _call_nodes(path: Path) -> list[ast.Call]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    visitor = _ReachableCallCollector()
    visitor.visit(tree)
    return visitor.calls

def _in_range(node: ast.Call, span: list[int]) -> bool:
    return span[0] <= node.lineno <= span[1]


def _printed_marker(node: ast.Call, marker: str) -> bool:
    return (isinstance(node.func, ast.Name) and node.func.id == "print"
            and node.args and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == marker)


def _player_command(node: ast.Call, command: str) -> bool:
    return (isinstance(node.func, ast.Attribute) and node.func.attr == "command"
            and node.args and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == command)


def load_ci_observations(root: Path = ROOT) -> dict[int, dict]:
    note = json.loads((root / RECEIPT).read_text(encoding="utf-8"))
    if note["schema"] != "fvillage.gdd_g01_ci_observations.v1":
        raise ValueError("Unexpected G01 CI receipt schema")
    if (note["ci_result"] != "completed_success"
            or len(note["source_commit"]) != 40
            or note["github_run_id"] <= 0
            or note["github_job_id"] <= 0
            or not note["ci_url"].endswith("/actions/runs/" + str(note["github_run_id"]))):
        raise ValueError("Receipt lacks a pinned successful run")
    # Source-immutability is the authoritative drift check. A previous CI
    # run cannot prove that newer, syntactically similar test code executed.
    # Git blob SHA-1 hashes the exact bytes and length, independent of the
    # availability of Git in a disposable CI or offline client environment.
    allowed_files = {
        note["runner_source"],
        note["telnet_test_source"],
        note["restart_test_source"],
    }
    if set(note.get("source_blob_sha1", {})) != allowed_files:
        raise ValueError("CI receipt must pin all and only the three source blobs")
    for name in sorted(allowed_files):
        raw = (root / name).read_bytes()
        git_blob = hashlib.sha1(
            b"blob " + str(len(raw)).encode("ascii") + b"\\0" + raw
        ).hexdigest()
        if git_blob != note["source_blob_sha1"][name]:
            raise ValueError("CI source blob mismatch: " + name)
    runner = (root / note["runner_source"]).read_text(encoding="utf-8")
    if not all(marker in runner for marker in (
            "telnet_playthrough.py", "post_restart_assertions.py",
            'evennia, "stop"', 'evennia, "start"')):
        raise ValueError("Receipt does not match actual restart runner")
    telnet_calls = _call_nodes(root / note["telnet_test_source"])
    restart_calls = _call_nodes(root / note["restart_test_source"])
    telnet_line_count = len((root / note["telnet_test_source"]).read_text(
        encoding="utf-8").splitlines())
    restart_line_count = len((root / note["restart_test_source"]).read_text(
        encoding="utf-8").splitlines())
    result = {}
    for case in note["cases"]:
        number = case["edge_number"]
        if not isinstance(number, int) or not 1 <= number <= 45 or number in result:
            raise ValueError("Invalid or duplicate GDD CI edge")
        for calls, line_count, marker_key, range_key in (
                (telnet_calls, telnet_line_count, "telnet_marker", "telnet_line_range"),
                (restart_calls, restart_line_count, "restart_marker", "restart_line_range")):
            span = case[range_key]
            start, end = span
            if not 1 <= start <= end <= line_count:
                raise ValueError("Incorrect CI source line range for edge %d" % number)
            markers = [node for node in calls
                       if _in_range(node, span)
                       and _printed_marker(node, case[marker_key])]
            if len(markers) != 1:
                raise ValueError("CI marker is not an executable print at claimed source "
                                 "for edge %d" % number)
        for command in case["player_commands"]:
            valid_calls = [node for node in telnet_calls
                           if _in_range(node, case["telnet_line_range"])
                           and _player_command(node, command)]
            if not command or not valid_calls:
                raise ValueError("Missing executable player command %r for edge %d" %
                                 (command, number))
        if not case["remaining"]:
            raise ValueError("CI edge missing unverified acceptance gaps")
        result[number] = {
            "ci_run_url": note["ci_url"],
            "ci_job_id": note["github_job_id"],
            "observed_on_commit": note["source_commit"],
            "client_source": note["telnet_test_source"],
            "client_lines": case["telnet_line_range"],
            "client_marker": case["telnet_marker"],
            "restart_source": note["restart_test_source"],
            "restart_lines": case["restart_line_range"],
            "restart_marker": case["restart_marker"],
            "client_commands": case["player_commands"],
            "observed_room": case["observed_room"],
            "observed_transition": case["observed_transition"],
            "remaining_gaps": case["remaining"],
            "proof_level": "historical_real_telnet_restart_partial_not_accepted",
        }
    return result
