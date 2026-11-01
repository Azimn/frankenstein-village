"""EDGE-15 behavioral, adversarial, two-account and JSON-restart state tests."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import bridge_case_state as case


def observation(day=3, account=11, mask_id=111, event=90):
    return {
        "day": day, "pattern": "daylight", "source_event_id": event,
        "witnesses": [{"account_id": account, "mask_id": mask_id}],
    }


def detective(state=None, day=3, hour=11, account=11, mask_id=111,
              event=101, observed=None):
    return case.examine(
        state, day=day, hour=hour, account_id=account,
        mask_id=mask_id, mask="DetectiveTester", event_id=event,
        observation=observation(day, account, mask_id) if observed is None else observed,
    )


def source(event=101, account=11, mask_id=111, day=3, hour=11):
    return {
        "id": event, "status": "complete",
        "kind": "village.bridge_plaque_examined",
        "actor": {
            "account_id": account, "mask_id": mask_id,
            "mask": "DetectiveTester",
        },
        "payload": {
            "day": day, "hour": hour, "location": "The Old Stone Bridge",
            "professional_calling": "detective", "observation_event_id": 90,
        },
        "consequence": {
            "case_exam_event_id": event, "observation_event_id": 90,
            "pattern": "daylight", "finding": "physical_marks_only",
        },
    }


def chronicler(state, *, day=3, hour=12, account=22, mask_id=222,
              event=102, signed=None):
    return case.publish(
        state, day=day, hour=hour, account_id=account,
        mask_id=mask_id, mask="ChroniclerTester", event_id=event,
        source=source() if signed is None else signed,
    )


class BridgeCaseEdge15Tests(unittest.TestCase):
    def test_two_distinct_accounts_sign_physical_examination_and_bulletin(self):
        state, ok, why = detective()
        self.assertTrue(ok, why)
        before = copy.deepcopy(state)
        published, ok, why = chronicler(state)
        self.assertTrue(ok, why)
        self.assertEqual(state, before, "The pure transition mutated its input")
        exam = published["case_examinations"][0]
        bulletin = published["case_bulletins"][0]
        self.assertEqual(bulletin["source_event_id"], exam["event_id"])
        self.assertEqual(bulletin["observation_event_id"], 90)
        self.assertNotEqual(bulletin["account_id"], exam["account_id"])
        text = " ".join(case.case_lines(published, 3))
        self.assertIn("bulletin event 102", text)
        self.assertIn("Detective source 101", text)
        self.assertIn("do not identify a culprit", text)

    def test_json_roundtrip_and_next_day_history_without_resetting_truth(self):
        state, ok, why = detective()
        self.assertTrue(ok, why)
        state, ok, why = chronicler(state)
        self.assertTrue(ok, why)
        restarted = json.loads(json.dumps(state))
        self.assertEqual(restarted, state)
        self.assertIn("No independently published", " ".join(case.case_lines(restarted, 4)))
        later, ok, why = detective(
            restarted, day=4, hour=10, event=103,
            observed=observation(day=4, event=92),
        )
        self.assertTrue(ok, why)
        later_source = source(event=103, day=4, hour=10)
        later_source["payload"]["observation_event_id"] = 92
        later_source["consequence"]["observation_event_id"] = 92
        later, ok, why = chronicler(
            later, day=4, hour=11, event=104, signed=later_source,
        )
        self.assertTrue(ok, why)
        self.assertEqual([b["event_id"] for b in later["case_bulletins"]], [102, 104])

    def test_no_examination_without_firsthand_physical_observation(self):
        for observed in (
            {}, observation(day=2), observation(account=999),
            {**observation(), "source_event_id": 0},
            {**observation(), "pattern": "supernatural"},
        ):
            state, ok, why = detective(observed=observed)
            self.assertFalse(ok, why)
            self.assertFalse(state.get("case_examinations"))
        state, ok, why = detective(day=0)
        self.assertFalse(ok)
        state, ok, why = detective(account=True)
        self.assertFalse(ok)

    def test_same_account_role_switch_and_duplicate_examination_rejected(self):
        state, ok, why = detective()
        self.assertTrue(ok, why)
        same, ok, why = chronicler(state, account=11)
        self.assertFalse(ok)
        self.assertIn("independent account", why)
        self.assertNotIn("case_bulletins", same)
        duplicate, ok, why = detective(state, event=105)
        self.assertFalse(ok)
        self.assertEqual(duplicate, state)

    def test_forged_or_failed_source_and_wrong_profession_rejected(self):
        state, ok, why = detective()
        self.assertTrue(ok, why)
        edits = [
            ("status", "consequence_failed"),
            ("kind", "village.bridge_plaque_culprit_proven"),
            ("id", 999),
        ]
        for field, value in edits:
            forged = source()
            forged[field] = value
            unchanged, ok, why = chronicler(state, signed=forged)
            self.assertFalse(ok, (field, why))
            self.assertEqual(unchanged, state)
        for group, field, value in [
            ("actor", "account_id", 999),
            ("actor", "mask_id", 999),
            ("actor", "mask", "Impostor"),
            ("payload", "professional_calling", "chronicler"),
            ("payload", "location", "Village Square"),
            ("payload", "day", 2),
            ("payload", "hour", True),
            ("payload", "observation_event_id", 777),
            ("consequence", "case_exam_event_id", 999),
            ("consequence", "pattern", "ghost"),
            ("consequence", "finding", "culprit_proven"),
        ]:
            forged = source()
            forged[group][field] = value
            unchanged, ok, why = chronicler(state, signed=forged)
            self.assertFalse(ok, (group, field, why))
            self.assertEqual(unchanged, state)

    def test_physical_witness_and_observation_event_require_strict_identity(self):
        for bad in (11.0, True):
            with self.subTest(account=bad):
                observed = observation()
                observed["witnesses"][0]["account_id"] = bad
                _state, ok, _why = detective(observed=observed)
                self.assertFalse(ok)
        for bad in (111.0, True):
            with self.subTest(mask=bad):
                observed = observation()
                observed["witnesses"][0]["mask_id"] = bad
                self.assertFalse(detective(observed=observed)[1])
        observed = observation()
        observed["day"] = 3.0
        self.assertFalse(detective(observed=observed)[1])
        observed = observation()
        observed["source_event_id"] = 101
        self.assertFalse(detective(observed=observed)[1])
        self.assertFalse(detective(observed=observation(), event=90)[1])

    def test_public_bulletin_requires_exact_signed_integer_source(self):
        state, ok, why = detective()
        self.assertTrue(ok, why)
        for group, field, bad in (
            ("actor", "account_id", 11.0),
            ("actor", "mask_id", 111.0),
            ("payload", "observation_event_id", 90.0),
            ("consequence", "case_exam_event_id", 101.0),
            ("consequence", "observation_event_id", 90.0),
        ):
            with self.subTest(group=group, field=field):
                forged = source()
                forged[group][field] = bad
                changed, ok, _why = chronicler(state, signed=forged)
                self.assertFalse(ok)
                self.assertEqual(changed, state)
        forged = source()
        forged["id"] = 101.0
        self.assertFalse(chronicler(state, signed=forged)[1])
        changed, ok, _why = chronicler(state, event=101)
        self.assertFalse(ok)
        self.assertEqual(changed, state)

    def test_tampered_persisted_examination_cannot_publish(self):
        state, ok, why = detective()
        self.assertTrue(ok, why)
        for key, bad in (("account_id", 11.0),
                         ("mask_id", 111.0),
                         ("event_id", 101.0),
                         ("observation_event_id", 90.0),
                         ("hour", 11.0),
                         ("day", 3.0)):
            with self.subTest(field=key):
                altered = copy.deepcopy(state)
                altered["case_examinations"][0][key] = bad
                changed, ok, _why = chronicler(altered)
                self.assertFalse(ok)
                self.assertEqual(changed, altered)
        altered = copy.deepcopy(state)
        altered["case_examinations"][0]["hour"] = 13
        self.assertFalse(chronicler(altered, hour=12)[1])

    def test_first_ledger_event_can_be_original_observation(self):
        # An observation may legitimately be world event 1. The bridge
        # preflight must use a distinct synthetic ID, never a hardcoded 1.
        observed = observation(event=1)
        state, ok, reason = detective(event=2, observed=observed)
        self.assertTrue(ok, reason)
        signed = source(event=2)
        signed["payload"]["observation_event_id"] = 1
        signed["consequence"]["observation_event_id"] = 1
        published, ok, reason = chronicler(state, event=3, signed=signed)
        self.assertTrue(ok, reason)
        self.assertEqual(published["case_bulletins"][0]["source_event_id"], 2)
        self.assertEqual(published["case_bulletins"][0]["observation_event_id"], 1)
        self.assertFalse(chronicler(state, event=1, signed=signed)[1])

    def test_no_publication_without_source_or_with_wrong_time(self):
        state, ok, why = chronicler({})
        self.assertFalse(ok)
        state, ok, why = detective()
        self.assertTrue(ok, why)
        for changes in ({"day": 4}, {"hour": 10}, {"account": True},
                        {"event": 0}):
            _, ok, why = chronicler(state, **changes)
            self.assertFalse(ok, changes)
        signed, ok, why = chronicler(state)
        self.assertTrue(ok, why)
        duplicate, ok, why = chronicler(signed, event=109)
        self.assertFalse(ok)
        self.assertEqual(duplicate, signed)



class BridgeWitnessAdapterTests(unittest.TestCase):
    """Execute the actual Evennia adapter functions with only IO mocked."""

    def test_second_witness_signs_own_source_and_detective_rejects_forgery(self):
        import ast
        from contextlib import nullcontext
        from types import ModuleType, SimpleNamespace
        from unittest.mock import patch

        source_path = Path(__file__).resolve().parents[2] / (
            "spike/fvillage/world/public_mysteries.py"
        )
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        names = {"observe_bridge", "examine_bridge_case"}
        functions = [node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name in names]
        self.assertEqual({node.name for node in functions}, names)

        first = {"account_id": 22, "mask_id": 222, "mask": "FirstWitness",
                 "source_event_id": 90}
        second = {"account_id": 11, "mask_id": 111, "mask": "DetectiveTester"}
        row = {
            "key": "3:10:clear:daylight", "day": 3, "hour": 10,
            "weather": "clear", "pattern": "daylight", "detail": "screws",
            "source_event_id": 90, "witnesses": [first],
        }
        registry = {"id": "PUBLIC-BRIDGE-PLAQUE", "observations": [row]}
        events = {
            90: {
                "id": 90, "status": "complete",
                "kind": "public_mystery.bridge_plaque.observed",
                "actor": {"account_id": 22, "mask_id": 222,
                          "mask": "FirstWitness"},
                "payload": {
                    "public_mystery_id": "PUBLIC-BRIDGE-PLAQUE",
                    "day": 3, "hour": 10, "weather": "clear",
                    "pattern": "daylight",
                },
            },
        }
        published = []

        def get_mystery(_ident):
            return copy.deepcopy(registry)

        def save(updated):
            registry.clear()
            registry.update(copy.deepcopy(updated))

        def ref(player):
            return {"account_id": player.account.id,
                    "mask_id": player.id, "mask": player.key}

        def publish(kind, *, actor, payload, consequence=None):
            event_id = max(events) + 1
            event = {"id": event_id, "status": "complete", "kind": kind,
                     "actor": ref(actor), "payload": payload}
            if consequence is not None:
                event["consequence"] = consequence(event)
            events[event_id] = event
            published.append(event_id)
            return event

        player = SimpleNamespace(
            id=111, key="DetectiveTester",
            account=SimpleNamespace(id=11), has_account=True,
            location=SimpleNamespace(key="The Old Stone Bridge"),
        )
        env = {
            "copy": copy, "BRIDGE_PLAQUE_ID": "PUBLIC-BRIDGE-PLAQUE",
            "get_public_mystery": get_mystery, "_save": save,
            "_metric": lambda **kw: None, "_player_ref": ref,
            "_clock": lambda: (3, 10), "_weather": lambda: "clear",
            "bridge_plaque_state": lambda *args: {
                "pattern": "daylight", "detail": "screws",
            },
        }
        exec(compile(ast.Module(body=functions, type_ignores=[]),
                     str(source_path), "exec"), env)

        world_events = ModuleType("world.events")
        world_events.publish_world_event = publish
        world_events.get_event_ledger = lambda: SimpleNamespace(
            get_event=lambda event_id: copy.deepcopy(events.get(event_id))
        )
        callings = ModuleType("world.callings")
        callings.active_calling = lambda _player: "detective"
        django = ModuleType("django")
        django_db = ModuleType("django.db")
        django_db.transaction = SimpleNamespace(atomic=nullcontext)
        django.db = django_db
        modules = {
            "world.events": world_events, "world.callings": callings,
            "django": django, "django.db": django_db,
        }

        with patch.dict(sys.modules, modules):
            observed = env["observe_bridge"](player, day=3, hour=10,
                                             weather="clear")
            self.assertEqual(observed["source_event_id"], 90)
            self.assertEqual(observed["witnesses"][1]["source_event_id"], 91)
            self.assertEqual(events[91]["actor"]["account_id"], 11)
            self.assertEqual(len(published), 1)
            env["observe_bridge"](player, day=3, hour=10, weather="clear")
            self.assertEqual(len(published), 1, "repeat look must not double-sign")

            saved = json.loads(json.dumps(registry))
            self.assertEqual(saved["observations"][0]["source_event_id"], 90)
            event, error = env["examine_bridge_case"](player)
            self.assertIsNone(error)
            self.assertEqual(event["id"], 92)
            self.assertEqual(registry["case_examinations"][0]
                             ["observation_event_id"], 91)

            # A fresh village day would be needed for a second examination.
            # Reset only the isolated test fixture, never the canonical ledger.
            registry.pop("case_examinations")
            for invalid in ("unsigned", "borrowed", "forged_actor",
                            "failed", "wrong_pattern", "float_id"):
                with self.subTest(invalid=invalid):
                    registry["observations"] = copy.deepcopy(saved["observations"])
                    events[91]["status"] = "complete"
                    events[91]["actor"] = ref(player)
                    events[91]["payload"]["pattern"] = "daylight"
                    if invalid == "unsigned":
                        registry["observations"][0]["witnesses"][1].pop(
                            "source_event_id"
                        )
                    elif invalid == "borrowed":
                        registry["observations"][0]["witnesses"][1][
                            "source_event_id"] = 90
                    elif invalid == "forged_actor":
                        events[91]["actor"]["account_id"] = 22
                    elif invalid == "failed":
                        events[91]["status"] = "consequence_failed"
                    elif invalid == "wrong_pattern":
                        events[91]["payload"]["pattern"] = "rainwater"
                    elif invalid == "float_id":
                        registry["observations"][0]["witnesses"][1][
                            "source_event_id"] = 91.0
                    before = copy.deepcopy(registry)
                    count = len(published)
                    denied, reason = env["examine_bridge_case"](player)
                    self.assertIsNone(denied)
                    self.assertTrue("source" in reason or "signed event ID" in reason, reason)
                    self.assertEqual(registry, before)
                    self.assertEqual(len(published), count)



if __name__ == "__main__":
    unittest.main()
