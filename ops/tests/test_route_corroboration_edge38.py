"""EDGE-38: independent, source-bound Hound/Wanderer route work."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import route_surveys as r


def prepared():
    state, ok, error = r.field_decision(
        None, 4, "red_cord", "wanderer", "passability",
        False, 31, "Wanderer", 101,
    )
    assert ok, error
    state, ok, error = r.field_decision(
        state, 4, "red_cord", "hound", "protect",
        False, 32, "Hound", 102,
    )
    assert ok, error
    return state, {"day": 4, "event_id": 102, "account_id": 32, "mask": "Hound"}


def signed(role):
    is_hound = role == "hound"
    return {
        "id": 102 if is_hound else 101,
        "kind": "village.route_protected" if is_hound else "village.route_passability_observed",
        "status": "complete",
        "actor": {"account_id": 32 if is_hound else 31,
                  "mask": "Hound" if is_hound else "Wanderer"},
        "payload": {"site": "red_cord", "day": 4, "hour": 12,
                    "role": role, "action": "protect" if is_hound else "passability",
                    "location": "The Northern Treeline"},
        "consequence": {"site": "red_cord", "day": 4,
                        "role": role, "action": "protect" if is_hound else "passability",
                        "cord_object_id": 6, "square_room_id": 7,
                        "caution_marked": is_hound,
                        "interpretation": None if is_hound else "unmarked"},
    }


class Edge38Tests(unittest.TestCase):
    def test_two_distinct_accounts_create_a_causal_link_without_rewriting_history(self):
        state, marker = prepared()
        old = copy.deepcopy(state)
        result, ok, error = r.corroborate(state, 4, "red_cord", 102, 31, "Wanderer", 103)
        self.assertTrue(ok, error)
        self.assertEqual(result["field_decisions"]["wanderer"]["observation"], "unmarked")
        self.assertEqual(result["field_decisions"]["wanderer"]["corroboration"]["hound_event_id"], 102)
        self.assertEqual(old["field_decisions"]["wanderer"]["observation"], "unmarked")
        self.assertNotIn("corroboration", old["field_decisions"]["wanderer"])
        self.assertTrue(any("not that the route is safe" in s for s in r.field_lines(result)))

    def test_duplicate_and_account_switch_are_rejected(self):
        state, marker = prepared()
        result, ok, _ = r.corroborate(state, 4, "red_cord", 102, 31, "Wanderer", 103)
        self.assertTrue(ok)
        for aid, event in ((31, 104), (32, 104), (33, 104)):
            after, ok, error = r.corroborate(result, 4, "red_cord", 102, aid, "X", event)
            self.assertFalse(ok, error)
            self.assertEqual(after, result)
        after, ok, error = r.corroborate(state, 4, "red_cord", 102, 32, "H", 103)
        self.assertFalse(ok)
        self.assertIn("separate", error)
        after, ok, error = r.corroborate(state, 4, "red_cord", 102, 31, "Imposter", 103)
        self.assertFalse(ok)
        self.assertIn("original Wanderer", error)

    def test_same_account_cannot_supply_both_professional_sources(self):
        state, _ = prepared()
        state["field_decisions"]["hound"]["account_id"] = 31
        after, ok, reason = r.corroborate(
            state, 4, "red_cord", 102, 31, "Wanderer", 103
        )
        self.assertFalse(ok)
        self.assertIn("separate Wanderer account", reason)
        self.assertNotIn("corroboration", after["field_decisions"]["wanderer"])

    def test_missing_hound_or_wanderer_or_wrong_marker_fails_closed(self):
        for role in ("hound", "wanderer"):
            state, marker = prepared()
            del state["field_decisions"][role]
            after, ok, _ = r.corroborate(state, 4, "red_cord", 102, 31, "Wanderer", 103)
            self.assertFalse(ok)
            self.assertNotIn("corroboration", after["field_decisions"].get("wanderer", {}))
        state, marker = prepared()
        for site, source in (("river_gauge", 102), ("red_cord", 999)):
            after, ok, _ = r.corroborate(state, 4, site, source, 31, "Wanderer", 103)
            self.assertFalse(ok)
            self.assertEqual(after, state)

    def test_bad_ids_clock_rewind_and_same_event_fail_closed(self):
        state, _ = prepared()
        for source, aid, event in ((True, 31, 103), (102, 0, 103),
                                   (102, 31, -1), (102, 31, 102),
                                   (102, 31, 101)):
            after, ok, _ = r.corroborate(state, 4, "red_cord", source, aid, "Wanderer", event)
            self.assertFalse(ok)
            self.assertEqual(after, state)
        after, ok, reason = r.corroborate(state, 3, "red_cord", 102, 31, "Wanderer", 103)
        self.assertFalse(ok)
        self.assertIn("later village day", reason)

    def test_marker_source_rejects_stale_and_forged(self):
        state, marker = prepared()
        hound = state["field_decisions"]["hound"]
        self.assertTrue(r.verify_caution_marker(marker, hound, 4))
        for key, bad in (("day", 3), ("event_id", 999), ("account_id", 31),
                         ("mask", "Another"), ("event_id", True)):
            forged = dict(marker, **{key: bad})
            self.assertFalse(r.verify_caution_marker(forged, hound, 4))

    def test_completed_source_verification_rejects_forgery(self):
        state, _ = prepared()
        for role in ("hound", "wanderer"):
            entry = state["field_decisions"][role]
            original = signed(role)
            self.assertTrue(r.verify_signed_field_source(
                original, entry, role, 4, 13, 6, 7
            ))
            for section, key, bad in (
                ("root", "status", "consequence_failed"),
                ("root", "kind", "village.route_inspected"),
                ("actor", "account_id", 999),
                ("actor", "mask", "Forged"),
                ("payload", "day", 5),
                ("payload", "hour", 14),
                ("payload", "location", "Village Square"),
                ("payload", "role", "merchant"),
                ("consequence", "cord_object_id", 999),
                ("consequence", "square_room_id", 999),
                ("consequence", "day", 3),
            ):
                forged = copy.deepcopy(original)
                target = forged if section == "root" else forged[section]
                target[key] = bad
                self.assertFalse(r.verify_signed_field_source(
                    forged, entry, role, 4, 13, 6, 7
                ), (role, section, key))

    def test_json_restart_and_day_rollover_preserve_link(self):
        state, _ = prepared()
        linked, ok, _ = r.corroborate(state, 4, "red_cord", 102, 31, "Wanderer", 103)
        self.assertTrue(ok)
        restored = r.normalize(json.loads(json.dumps(linked)))
        self.assertEqual(restored, linked)
        later = r.refresh(restored, 5)
        self.assertEqual(later["field_decisions"], {})
        self.assertEqual(later["history"][-1]["field_decisions"]["wanderer"]["corroboration"]["event_id"], 103)

    def test_signed_later_day_hound_retie_preserves_prior_corroboration(self):
        first, _ = prepared()
        first, ok, why = r.corroborate(
            first, 4, "red_cord", 102, 31, "Wanderer", 103
        )
        self.assertTrue(ok, why)
        persisted = json.loads(json.dumps(first))
        next_day = r.refresh(persisted, 5)
        retied, ok, why = r.field_decision(
            next_day, 5, "red_cord", "hound", "protect", True,
            32, "Hound", 104, caution_day=4,
        )
        self.assertTrue(ok, why)
        self.assertTrue(retied["field_decisions"]["hound"]["retied_previous_day"])
        self.assertTrue(any("re-tied" in line for line in r.field_lines(retied)))
        self.assertEqual(
            retied["history"][-1]["field_decisions"]["wanderer"]
            ["corroboration"]["event_id"], 103,
        )
        self.assertEqual(r.normalize(json.loads(json.dumps(retied))), retied)
        for caution_day in (None, 5, 6, 0, True, 4.0):
            with self.subTest(caution_day=caution_day):
                denied, allowed, _ = r.field_decision(
                    next_day, 5, "red_cord", "hound", "protect", True,
                    32, "Hound", 104, caution_day=caution_day,
                )
                self.assertFalse(allowed)
                self.assertEqual(denied, next_day)

    def test_reconciled_route_adapter_keeps_both_canonical_services(self):
        import ast
        source = (Path(__file__).resolve().parents[2]
                  / "spike/fvillage/world/route_work.py").read_text(
                      encoding="utf-8"
                  )
        tree = ast.parse(source)
        names = {node.name for node in tree.body
                 if isinstance(node, ast.FunctionDef)}
        self.assertTrue({
            "_caution_marker", "_signed_prior_caution",
            "publish_advisory", "_corroboration_sources", "_corroborate",
        }.issubset(names))
        field = next(node for node in tree.body
                     if isinstance(node, ast.FunctionDef)
                     and node.name == "field_action")
        calls = {node.func.id for node in ast.walk(field)
                 if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name)}
        self.assertIn("_corroborate", calls)
        self.assertIn("_signed_prior_caution", calls)


    def test_unverified_joint_metadata_does_not_survive_normalization(self):
        state, _ = prepared()
        state["field_decisions"]["wanderer"]["corroboration"] = {
            "event_id": 103, "hound_event_id": 999, "account_id": 31,
            "mask": "Wanderer", "observation": "marked_caution",
        }
        restored = r.normalize(state)
        self.assertNotIn("corroboration", restored["field_decisions"]["wanderer"])


    def test_public_corroboration_requires_completed_three_event_chain(self):
        state, marker = prepared()
        state, ok, reason = r.corroborate(
            state, 4, "red_cord", 102, 31, "Wanderer", 103
        )
        self.assertTrue(ok, reason)
        hound, wanderer = signed("hound"), signed("wanderer")
        joint = {
            "id": 103, "status": "complete",
            "kind": "village.route_caution_corroborated",
            "actor": {"account_id": 31, "mask": "Wanderer", "mask_id": 88},
            "payload": {
                "site": "red_cord", "day": 4, "hour": 13,
                "role": "wanderer", "action": "corroborate",
                "location": "The Northern Treeline", "cord_object_id": 6,
                "hound_source_event_id": 102,
                "wanderer_source_event_id": 101,
            },
            "consequence": {
                "site": "red_cord", "day": 4,
                "role": "wanderer", "action": "corroborate",
                "cord_object_id": 6, "square_room_id": 7,
                "hound_source_event_id": 102,
                "wanderer_source_event_id": 101,
                "physical_caution_present": True,
            },
        }
        def verified(event=joint, h=hound, w=wanderer, board=state, physical=marker):
            return r.verify_signed_corroboration(
                board, event, h, w, day=4, hour=13, cord_id=6,
                square_id=7, marker=physical,
            )
        self.assertTrue(verified())
        self.assertTrue(verified(board=json.loads(json.dumps(state))))
        for section, key, bad in (
            ("root", "status", "failed"),
            ("root", "kind", "village.route_passability_observed"),
            ("root", "id", 999),
            ("actor", "account_id", 32),
            ("actor", "mask", "Impostor"),
            ("actor", "mask_id", True),
            ("payload", "day", 5),
            ("payload", "hour", 11),
            ("payload", "location", "Village Square"),
            ("payload", "cord_object_id", 9),
            ("payload", "hound_source_event_id", 999),
            ("payload", "wanderer_source_event_id", 999),
            ("consequence", "square_room_id", 9),
            ("consequence", "cord_object_id", 9),
            ("consequence", "physical_caution_present", False),
        ):
            with self.subTest(section=section, key=key):
                forged = copy.deepcopy(joint)
                target = forged if section == "root" else forged[section]
                target[key] = bad
                self.assertFalse(verified(event=forged))
        for source in (hound, wanderer):
            forged = copy.deepcopy(source)
            forged["status"] = "failed"
            self.assertFalse(verified(
                h=forged if source is hound else hound,
                w=forged if source is wanderer else wanderer,
            ))
        self.assertFalse(verified(physical=dict(marker, event_id=999)))
        self.assertFalse(verified(board=r.refresh(state, 5)))

    def test_public_status_suppresses_forged_joint_without_mutating_board(self):
        import ast
        from types import SimpleNamespace
        path = (Path(__file__).resolve().parents[2]
                / "spike/fvillage/world/route_work.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        node = next(n for n in tree.body
                    if isinstance(n, ast.FunctionDef) and n.name == "status_lines")
        import copy as _copy
        state, marker = prepared()
        state, ok, _ = r.corroborate(state, 4, "red_cord", 102, 31, "Wanderer", 103)
        self.assertTrue(ok)
        square = SimpleNamespace(id=7, db=SimpleNamespace(daily_route_survey=state))
        cord = SimpleNamespace(
            id=6, location=SimpleNamespace(key="The Northern Treeline"),
            db=SimpleNamespace(landmark_id="red_cord", route_caution=marker),
        )
        sources = {
            101: signed("wanderer"), 102: signed("hound"),
            103: {
                "id": 103, "status": "complete",
                "kind": "village.route_caution_corroborated",
                "actor": {"account_id": 31, "mask": "Wanderer", "mask_id": 88},
                "payload": {
                    "site": "red_cord", "day": 4, "hour": 13,
                    "role": "wanderer", "action": "corroborate",
                    "location": "The Northern Treeline", "cord_object_id": 6,
                    "hound_source_event_id": 102, "wanderer_source_event_id": 101,
                },
                "consequence": {
                    "site": "red_cord", "day": 4, "role": "wanderer",
                    "action": "corroborate", "cord_object_id": 6,
                    "square_room_id": 7, "hound_source_event_id": 102,
                    "wanderer_source_event_id": 101,
                    "physical_caution_present": True,
                },
            },
        }
        ns = {
            "_square": lambda: square, "_day_hour": lambda: (4, 13),
            "route_surveys": r,
            "get_event_ledger": lambda: SimpleNamespace(
                get_event=lambda eid: sources.get(eid)),
            "search": SimpleNamespace(search_object=lambda key: [cord]),
            "LANDMARKS": {
                site: {"key": "a frayed red cord", "room": "The Northern Treeline"}
                for site in r.SITES
            },
            "_caution_marker": lambda raw: raw,
            # The public adapter now separately verifies Hound provenance.
            # Preserve that requirement in this isolated EDGE-38 AST fixture.
            "_signed_hound_source": lambda square_obj, day, hour: (
                {"source_event_id": 102}
                if r.verify_caution_marker(
                    marker, state["field_decisions"]["hound"], day
                ) and r.verify_signed_field_source(
                    sources[102], state["field_decisions"]["hound"],
                    "hound", day, hour, cord.id, square_obj.id
                ) else None
            ),
            "_verified_notice": lambda *_args: False,
        }
        module = ast.Module(body=[node], type_ignores=[])
        exec(compile(module, str(path), "exec"), ns)
        snapshot = _copy.deepcopy(state)
        good = ns["status_lines"]()
        self.assertIn("independently rechecked", good)
        sources[103]["consequence"]["physical_caution_present"] = False
        bad = ns["status_lines"]()
        self.assertNotIn("independently rechecked", bad)
        self.assertIn("stored route corroboration is unverified", bad)
        self.assertEqual(state, snapshot)


if __name__ == "__main__":
    unittest.main()
