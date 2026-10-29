"""GDD-EDGE-13: signed Wanderer observation -> Chronicler public map.

Pure behavioral, negative, day-rollover and JSON restart tests. Real telnet
and process-restart checks live in the existing spike integration suite.
"""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import route_surveys as r


def wanderer(day=4, account=21, event=101, marked=False):
    state, ok, error = r.field_decision(
        None, day, "red_cord", "wanderer", "passability",
        marked, account, "WandererTester", event,
    )
    assert ok, error
    return state


class ChroniclerWandererAdvisoryTests(unittest.TestCase):
    def test_distinct_accounts_publish_actual_snapshot(self):
        state = wanderer()
        published, ok, error = r.publish_advisory(
            state, 4, 22, "ChroniclerTester", 102, 101,
        )
        self.assertTrue(ok, error)
        item = published["advisory"]
        self.assertEqual(item["source_account_id"], 21)
        self.assertEqual(item["account_id"], 22)
        self.assertEqual(item["source_event_id"], 101)
        self.assertEqual(item["event_id"], 102)
        self.assertEqual(item["observation"], "unmarked")
        self.assertEqual(item["version"], 1)
        self.assertIn("not a current safety guarantee", r.advisory_lines(published)[0])
        self.assertIsNone(state["advisory"], "Input must not be mutated")

    def test_first_ledger_event_can_be_published_by_real_adapter(self):
        # Execute the actual production adapter with a source whose event
        # ID is 1. A hard-coded preflight event 1 previously rejected it.
        import ast
        from contextlib import nullcontext
        from types import SimpleNamespace

        path = (Path(__file__).resolve().parents[2]
                / "spike/fvillage/world/route_work.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        functions = [
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "publish_advisory"
        ]
        self.assertEqual(len(functions), 1)
        namespace = {}
        exec(compile(ast.fix_missing_locations(
            ast.Module(body=functions, type_ignores=[])), str(path), "exec"),
            namespace)

        square = SimpleNamespace(
            id=42,
            db=SimpleNamespace(daily_route_survey=wanderer(event=1)),
            tags=SimpleNamespace(has=lambda name, category=None: name == "ic"),
        )
        chronicler = SimpleNamespace(
            id=9, key="ChroniclerTester",
            account=SimpleNamespace(id=22), location=square,
        )
        source_event = {
            "id": 1, "status": "complete",
            "kind": "village.route_passability_observed",
            "payload": {"site": "red_cord", "day": 4},
            "actor": {"account_id": 21},
        }
        signed = []

        def publish(kind, *, actor, payload, consequence):
            self.assertEqual(kind, "village.route_map_published")
            self.assertIs(actor, chronicler)
            self.assertEqual(payload["source_event_id"], 1)
            event = {"id": 2, "kind": kind}
            event["consequence"] = consequence(event)
            signed.append(event)
            return event

        namespace.update({
            "active_calling": lambda mask: "chronicler",
            "_square": lambda: square,
            "_day_hour": lambda: (4, 21),
            "route_surveys": r,
            "get_event_ledger": lambda: SimpleNamespace(
                get_event=lambda ident: source_event if ident == 1 else None),
            "transaction": SimpleNamespace(atomic=nullcontext),
            "record_participation": lambda *args, **kwargs: None,
            "publish_world_event": publish,
        })
        result, error = namespace["publish_advisory"](chronicler)
        self.assertIsNone(error)
        self.assertEqual(result["event_id"], 2)
        self.assertEqual(result["source_event_id"], 1)
        self.assertEqual(len(signed), 1)
        advisory = square.db.daily_route_survey["advisory"]
        self.assertEqual(advisory["source_event_id"], 1)
        self.assertEqual(advisory["event_id"], 2)
        self.assertEqual(advisory["account_id"], 22)

    def test_no_wanderer_source_no_publication(self):
        result, ok, reason = r.publish_advisory(None, 4, 22, "C", 102, 101)
        self.assertFalse(ok)
        self.assertIn("Wanderer", reason)
        self.assertIsNone(result["advisory"])

    def test_self_attestation_is_not_two_account_work(self):
        source = wanderer()
        result, ok, reason = r.publish_advisory(
            source, 4, 21, "W", 102, 101,
        )
        self.assertFalse(ok)
        self.assertIn("independent", reason)
        self.assertIsNone(result["advisory"])

    def test_forged_source_and_invalid_ids_fail_closed(self):
        source = wanderer()
        for account, event, source_id in (
            (22, 102, 999), (True, 102, 101), (22, False, 101),
            (22, 102, True), (0, 102, 101), (22, -1, 101),
            (22, 101, 101),
        ):
            result, ok, reason = r.publish_advisory(
                source, 4, account, "C", event, source_id,
            )
            self.assertFalse(ok, reason)
            self.assertIsNone(result["advisory"])
        self.assertIsNone(source["advisory"])

    def test_duplicate_and_stale_day_are_denied_without_rewrite(self):
        state = wanderer()
        state, ok, error = r.publish_advisory(
            state, 4, 22, "C", 102, 101,
        )
        self.assertTrue(ok, error)
        original = copy.deepcopy(state)
        duplicate, ok, reason = r.publish_advisory(
            state, 4, 23, "Another", 103, 101,
        )
        self.assertFalse(ok)
        self.assertIn("already published", reason)
        self.assertEqual(duplicate, original)
        next_day = r.refresh(state, 5)
        stale, ok, reason = r.publish_advisory(
            next_day, 4, 23, "Late", 104, 101,
        )
        self.assertFalse(ok)
        self.assertIn("later village day", reason)
        self.assertEqual(stale, next_day)

    def test_later_hound_caution_does_not_rewrite_map(self):
        state = wanderer()
        state, ok, error = r.publish_advisory(
            state, 4, 22, "C", 102, 101,
        )
        self.assertTrue(ok, error)
        later, ok, error = r.field_decision(
            state, 4, "red_cord", "hound", "protect", False,
            23, "Hound", 103,
        )
        self.assertTrue(ok, error)
        self.assertEqual(later["advisory"]["observation"], "unmarked")
        self.assertEqual(later["field_decisions"]["hound"]["event_id"], 103)

    def test_json_restart_and_next_day_archive(self):
        state = wanderer(marked=True)
        state, ok, error = r.publish_advisory(
            state, 4, 22, "C", 102, 101,
        )
        self.assertTrue(ok, error)
        reloaded = r.normalize(json.loads(json.dumps(state)))
        self.assertEqual(reloaded["advisory"], state["advisory"])
        day5 = r.refresh(reloaded, 5)
        self.assertIsNone(day5["advisory"])
        self.assertEqual(day5["history"][-1]["advisory"]["source_event_id"], 101)
        self.assertIn("marked caution", r.advisory_lines(reloaded)[0])

    def test_corrupt_persisted_advisory_cannot_gain_authority(self):
        state = wanderer()
        state["advisory"] = {
            "version": True, "source_day": 4, "observation": "safe",
            "account_id": 22, "event_id": 102, "source_account_id": 21,
            "source_event_id": 101,
        }
        self.assertIsNone(r.normalize(state)["advisory"])
        # Even plausible-looking stored data cannot point to another actor's
        # source event or change the witnessed condition after publication.
        valid = wanderer()
        published, ok, reason = r.publish_advisory(
            valid, 4, 22, "C", 102, 101,
        )
        self.assertTrue(ok, reason)
        forged = copy.deepcopy(published)
        forged["advisory"]["source_account_id"] = 999
        self.assertIsNone(r.normalize(forged)["advisory"])
        forged = copy.deepcopy(published)
        forged["advisory"]["observation"] = "marked_caution"
        self.assertIsNone(r.normalize(forged)["advisory"])

    def test_solo_wanderer_report_stays_public_without_editor(self):
        # A lone Wanderer still changes the signed public field record.
        # The missing Chronicler must not create a fictional map edition.
        state = wanderer(marked=True)
        self.assertIsNone(state["advisory"])
        self.assertIn("Wanderer's passage observation", r.field_lines(state)[0])
        board = "\n".join(r.advisory_lines(state))
        self.assertIn("Solo fallback:", board)
        self.assertIn("signed event 101", board)
        self.assertIn("not an edited map", board)
        self.assertIsNone(r.normalize(json.loads(json.dumps(state)))["advisory"])
        tomorrow = r.refresh(state, 5)
        self.assertIsNone(tomorrow["advisory"])
        self.assertEqual(tomorrow["history"][-1]["field_decisions"]["wanderer"]["event_id"], 101)
        self.assertIsNone(tomorrow["history"][-1]["advisory"])

    def test_ordinary_solo_landmark_inspection_does_not_require_either_calling(self):
        # An unaccompanied player can contribute to the existing route board,
        # but neither a Wanderer testimony nor an edited map is invented.
        state, ok, error = r.report(None, 4, "market_scale", 31, "SoloResident", 104)
        self.assertTrue(ok, error)
        self.assertEqual(state["reports"]["market_scale"]["event_id"], 104)
        self.assertFalse(r.complete(state))
        self.assertNotIn("wanderer", state["field_decisions"])
        self.assertIsNone(state["advisory"])
        self.assertIn("any player may inspect", "\n".join(r.advisory_lines(state)))
        tomorrow = r.refresh(json.loads(json.dumps(state)), 5)
        self.assertEqual(tomorrow["history"][-1]["reports"]["market_scale"]["event_id"], 104)
        self.assertFalse(tomorrow["history"][-1]["completed"])
        self.assertIsNone(tomorrow["history"][-1]["advisory"])


    def test_signed_publication_readback_requires_completed_canonical_event(self):
        state = wanderer()
        published, ok, reason = r.publish_advisory(
            state, 4, 22, "ChroniclerTester", 102, 101,
        )
        self.assertTrue(ok, reason)
        signed = {
            "id": 102, "kind": "village.route_map_published",
            "status": "complete",
            "actor": {"account_id": 22, "mask": "ChroniclerTester"},
            "payload": {"site": "red_cord", "day": 4, "version": 1,
                        "source_event_id": 101, "source_account_id": 21},
            "consequence": {"square_room_id": 42, "day": 4, "version": 1,
                            "source_event_id": 101, "source_account_id": 21,
                            "observation": "unmarked"},
        }
        check = lambda event: r.verified_advisory_publication(
            published, event, square_id=42,
        )
        self.assertTrue(check(signed))
        self.assertTrue(check(json.loads(json.dumps(signed))))
        self.assertFalse(check(None))
        self.assertFalse(check({}))
        for field, invalid in (
            ("id", 999), ("status", "failed"),
            ("kind", "village.route_inspected"),
        ):
            changed = copy.deepcopy(signed)
            changed[field] = invalid
            self.assertFalse(check(changed), field)
        for section, key, invalid in (
            ("actor", "account_id", 999),
            ("actor", "account_id", True),
            ("actor", "mask", "ForgedChronicler"),
            ("payload", "site", "market_scale"),
            ("payload", "day", 5),
            ("payload", "version", 2),
            ("payload", "source_event_id", 999),
            ("payload", "source_account_id", 999),
            ("consequence", "square_room_id", 999),
            ("consequence", "day", 5),
            ("consequence", "version", 2),
            ("consequence", "source_event_id", 999),
            ("consequence", "source_account_id", 999),
            ("consequence", "observation", "marked_caution"),
        ):
            changed = copy.deepcopy(signed)
            changed[section][key] = invalid
            self.assertFalse(check(changed), (section, key))
        self.assertFalse(r.verified_advisory_publication(
            published, signed, square_id=True,
        ))
        self.assertTrue(check(signed), "Hostile probes must not mutate evidence")
        self.assertEqual(published["advisory"]["event_id"], 102)

    def test_public_readback_never_labels_ghost_publications_signed(self):
        # Execute the real Evennia adapter's public readback body with isolated
        # ledger and Square fixtures, without making a model or network call.
        import ast
        from types import SimpleNamespace
        path = (Path(__file__).resolve().parents[2] /
                "spike/fvillage/world/route_work.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and
                        node.name == "status_lines")
        scope = {}
        exec(compile(ast.fix_missing_locations(
            ast.Module(body=[function], type_ignores=[])),
            str(path), "exec"), scope)
        published, ok, reason = r.publish_advisory(
            wanderer(), 4, 22, "ChroniclerTester", 102, 101,
        )
        self.assertTrue(ok, reason)
        # A prior day with no advisory remains a normal archived route.
        square = SimpleNamespace(id=42, db=SimpleNamespace(
            daily_route_survey=published,
        ))
        scope.update({
            "_square": lambda: square, "_day_hour": lambda: (4, 21),
            "route_surveys": r, "LANDMARKS": {
                site: {"room": "Test Room", "key": site} for site in r.SITES
            },
            "get_event_ledger": lambda: SimpleNamespace(
                get_event=lambda ident: None),
        })
        untrusted = scope["status_lines"]()
        self.assertIn("unverified", untrusted)
        self.assertNotIn("Public route map v1", untrusted)
        self.assertNotIn("Chronicler ChroniclerTester (signed event 102)", untrusted)
        self.assertIn("Solo fallback", untrusted)
        self.assertEqual(square.db.daily_route_survey, published)



if __name__ == "__main__":
    unittest.main()
