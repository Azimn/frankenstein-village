"""GDD-EDGE-28: signed Healer source, independent Detective and durable cot."""
import copy
import json
import sys
import unittest
from collections import UserDict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))

from world import clinic_inquiry_state as rules


def fixture():
    assessment = dict(day=1, hour=21, account_id=11, mask_id=111,
                      mask="HealerTester", event_id=101)
    event = {
        "id": 101, "kind": "village.clinic_assess", "status": "complete",
        "actor": {"account_id": 11, "mask_id": 111, "mask": "HealerTester"},
        "payload": {"day": 1, "hour": 21, "professional_calling": "healer"},
        "consequence": {"room_id": 301, "assessment_event_id": 101,
                        "patient_condition": "cold"},
    }
    args = dict(day=1, hour=21, account_id=22, mask_id=222,
                mask="DetectiveTester", event_id=202, source_event_id=101,
                source_account_id=11, source_mask_id=111,
                source_day=1, source_hour=21, cot_id=401, room_id=301,
                case_item_id=501, case_well_id=601,
                interpretation="unrelated_illness")
    return assessment, event, args


class ClinicInquiryRules(unittest.TestCase):
    def test_signed_source_and_separate_account(self):
        assessment, event, args = fixture()
        self.assertTrue(rules.source_valid(event, assessment, 301))
        state, good, reason = rules.investigate(None, **args)
        self.assertTrue(good, reason)
        self.assertEqual(state["records"][0]["source_event_id"], 101)
        self.assertEqual(state["records"][0]["cot_id"], 401)
        self.assertEqual(state["records"][0]["case_item_id"], 501)
        self.assertEqual(state["records"][0]["case_well_id"], 601)
        self.assertEqual(state["records"][0]["alternative"], "possible_exposure")
        self.assertNotIn("cold", rules.public_lines(state, 1))
        self.assertNotIn("HealerTester", rules.public_lines(state, 1))

    def test_first_ledger_event_preview_then_distinct_detective_receipt(self):
        # A fresh WorldEventLedger gives the Healer event 1 and the
        # independent Detective event 2. Preflight must not pretend it is 1.
        _assessment, _source, args = fixture()
        args.update(source_event_id=1, event_id=None)
        original = {"records": []}
        before = copy.deepcopy(original)
        preview, good, reason = rules.investigate(
            original, preview=True, **args)
        self.assertTrue(good, reason)
        self.assertEqual(preview, before)
        self.assertEqual(original, before)

        # An unsigned preview must never be admitted as a signed record.
        _state, good, _reason = rules.investigate(original, **args)
        self.assertFalse(good)
        _state, good, _reason = rules.investigate(
            original, preview=True, **dict(args, event_id=2))
        self.assertFalse(good)
        _state, good, _reason = rules.investigate(
            original, **dict(args, event_id=1))
        self.assertFalse(good)

        committed, good, reason = rules.investigate(
            original, **dict(args, event_id=2))
        self.assertTrue(good, reason)
        self.assertEqual(committed["records"][0]["event_id"], 2)
        self.assertEqual(committed["records"][0]["source_event_id"], 1)
        self.assertEqual(original, before)

        # Duplicate patient-day and same-account signatures remain denied
        # even when the caller only requests an unsigned preview.
        _state, good, _reason = rules.investigate(
            committed, preview=True, **args)
        self.assertFalse(good)
        _state, good, _reason = rules.investigate(
            original, preview=True,
            **dict(args, account_id=args["source_account_id"]))
        self.assertFalse(good)
        _state, good, _reason = rules.investigate(
            original, preview=True,
            **dict(args, hour=20, source_hour=21))
        self.assertFalse(good)
        _state, good, _reason = rules.investigate(
            original, preview=True,
            **dict(args, source_event_id=0))
        self.assertFalse(good)

    def test_forged_or_failed_ledger_source_is_rejected(self):
        assessment, event, _ = fixture()
        for path, value in (
            (("kind",), "village.clinic_treat"),
            (("status",), "consequence_failed"),
            (("id",), 999),
            (("actor", "account_id"), 999),
            (("actor", "mask_id"), 999),
            (("actor", "mask"), "Impostor"),
            (("payload", "professional_calling"), "detective"),
            (("payload", "day"), 2),
            (("payload", "hour"), 20),
            (("consequence", "room_id"), 302),
            (("consequence", "assessment_event_id"), 999),
            (("consequence", "patient_condition"), "magic"),
        ):
            with self.subTest(path=path):
                forged = copy.deepcopy(event)
                target = forged
                for part in path[:-1]:
                    target = target[part]
                target[path[-1]] = value
                self.assertFalse(rules.source_valid(forged, assessment, 301))
        self.assertFalse(rules.source_valid(None, assessment, 301))
        self.assertFalse(rules.source_valid(event, None, 301))
        self.assertFalse(rules.source_valid(event, assessment, True))

    def test_missing_paired_healer_source_ids_are_not_signed(self):
        assessment, event, _args = fixture()
        for actor_key, assessment_key in (
            ("id", "event_id"), ("account_id", "account_id"),
            ("mask_id", "mask_id"), ("mask", "mask"),
        ):
            with self.subTest(missing=actor_key):
                corrupted_event = copy.deepcopy(event)
                corrupted_assessment = copy.deepcopy(assessment)
                if actor_key == "id":
                    corrupted_event["id"] = None
                else:
                    corrupted_event["actor"][actor_key] = None
                corrupted_assessment[assessment_key] = None
                self.assertFalse(rules.source_valid(
                    corrupted_event, corrupted_assessment, 301))

    def test_role_switching_and_forged_ids(self):
        _, _, args = fixture()
        for field, value in (("account_id", 11), ("account_id", True),
                             ("mask_id", 0), ("event_id", True),
                             ("source_event_id", -1), ("cot_id", 0),
                             ("room_id", "301"), ("case_well_id", None),
                             ("case_well_id", True), ("case_item_id", None),
                             ("case_item_id", True), ("case_item_id", 501.5),
                             ("interpretation", "confirmed_poisoning"),
                             ("day", True),
                             ("hour", 24), ("hour", -1)):
            with self.subTest(field=field, value=value):
                bad = dict(args, **{field: value})
                _state, good, _reason = rules.investigate(None, **bad)
                self.assertFalse(good)

    def test_duplicate_and_future_source(self):
        _, _, args = fixture()
        state, good, _ = rules.investigate(None, **args)
        self.assertTrue(good)
        for update in ({"event_id": 203}, {"day": 1, "hour": 22, "event_id": 203},
                       {"day": 2, "hour": 1, "event_id": 204},
                       {"day": 1, "hour": 20, "event_id": 205}):
            with self.subTest(update=update):
                _state, good, _reason = rules.investigate(
                    state, **dict(args, **update))
                self.assertFalse(good)

    def test_one_patient_day_and_bounded_history(self):
        state = None
        for day in range(1, 43):
            _, _, args = fixture()
            args.update(day=day, source_day=day, event_id=day * 10 + 2,
                        source_event_id=day * 10 + 1)
            state, good, reason = rules.investigate(state, **args)
            self.assertTrue(good, reason)
        self.assertEqual(len(state["records"]), rules.MAX_RECORDS)
        self.assertEqual(state["records"][-1]["day"], 42)
        self.assertEqual(state["records"][0]["day"], 7)

    def test_json_roundtrip_and_mapping_proxy(self):
        _, _, args = fixture()
        state, good, _ = rules.investigate(None, **args)
        self.assertTrue(good)
        restored = rules.normalize(json.loads(json.dumps(state)))
        self.assertEqual(state, restored)
        self.assertEqual(state, rules.normalize(UserDict(state)))
        restored["records"][0]["source_event_id"] = 999
        self.assertEqual(state["records"][0]["source_event_id"], 101)


    def test_public_inquiry_requires_two_real_signed_events(self):
        _assessment, source, args = fixture()
        state, good, reason = rules.investigate(None, **args)
        self.assertTrue(good, reason)
        inquiry = {
            "id": 202, "kind": "village.clinic_inquiry", "status": "complete",
            "actor": {"account_id": 22, "mask_id": 222, "mask": "DetectiveTester"},
            "payload": {"day": 1, "hour": 21, "professional_calling": "detective",
                        "cot_id": 401, "room_id": 301,
                        "case_item_id": 501, "case_item_key": rules.CASE_ITEM_KEY,
                        "case_well_id": 601, "case_item_toxin": 25,
                        "interpretation": "unrelated_illness",
                        "alternative": "possible_exposure",
                        "source_healer_event_id": 101, "source_healer_account_id": 11},
            "consequence": {"cot_id": 401, "room_id": 301,
                            "case_item_id": 501,
                            "case_well_id": 601, "case_item_toxin": 25,
                            "interpretation": "unrelated_illness",
                            "alternative": "possible_exposure",
                            "causal_status": "unproven",
                            "source_healer_event_id": 101,
                            "finding": "contested_clinic_cause",
                            "day": 1, "hour": 21},
        }
        events = {101: source, 202: inquiry}
        lookup = events.get
        line = rules.public_lines(state, 1, lookup)
        self.assertIn("signed as event 202", line)
        self.assertIn("Healer assessment event 101", line)
        self.assertIn("Competing interpretations", line)
        self.assertIn("physical specimen 501", line)
        self.assertIn("neither causal explanation is proven", line)
        self.assertNotIn("HealerTester", line)
        self.assertNotIn("cold", line)

        # Shape-valid persisted IDs are not signed without canonical events.
        self.assertIn("requires signed source inspection",
                      rules.public_lines(state, 1, lambda _id: None))
        self.assertIn("requires signed source inspection",
                      rules.public_lines(state, 1, lambda _id: (_ for _ in ()).throw(ValueError())))
        for event_id, field_path, value in (
            (202, ("status",), "consequence_failed"),
            (202, ("kind",), "village.clinic_assess"),
            (202, ("actor", "account_id"), 11),
            (202, ("payload", "cot_id"), 999),
            (202, ("payload", "case_item_id"), 999),
            (202, ("payload", "case_item_key"), "invented clue"),
            (202, ("payload", "case_well_id"), 999),
            (202, ("payload", "case_item_toxin"), None),
            (202, ("payload", "case_item_toxin"), 0),
            (202, ("payload", "case_item_toxin"), True),
            (202, ("payload", "case_item_toxin"), 25.0),
            (202, ("payload", "interpretation"), "confirmed_poisoning"),
            (202, ("payload", "alternative"), "confirmed_poisoning"),
            (202, ("consequence", "case_item_id"), 999),
            (202, ("consequence", "case_well_id"), 999),
            (202, ("consequence", "case_item_toxin"), None),
            (202, ("consequence", "case_item_toxin"), 26),
            (202, ("consequence", "interpretation"), "confirmed_poisoning"),
            (202, ("consequence", "alternative"), "confirmed_poisoning"),
            (202, ("consequence", "causal_status"), "confirmed"),
            (202, ("payload", "source_healer_event_id"), 999991),
            (202, ("consequence", "source_healer_event_id"), 999992),
            (202, ("consequence", "finding"), "diagnosis"),
            (202, ("consequence", "day"), 2),
            (101, ("status",), "consequence_failed"),
            (101, ("kind",), "village.clinic_treat"),
            (101, ("actor", "mask_id"), 999),
            (101, ("payload", "day"), 2),
            (101, ("consequence", "assessment_event_id"), 999993),
            (101, ("consequence", "room_id"), 999),
        ):
            with self.subTest(event_id=event_id, field_path=field_path):
                forged = copy.deepcopy(events)
                target = forged[event_id]
                for part in field_path[:-1]:
                    target = target[part]
                target[field_path[-1]] = value
                self.assertFalse(rules.signed_inquiry(
                    state["records"][0], forged.get))
                self.assertIn("requires signed source inspection",
                              rules.public_lines(state, 1, forged.get))
        self.assertEqual(state["records"][0]["event_id"], 202)

    def test_case_item_and_rival_hypotheses_are_required(self):
        _assessment, _event, args = fixture()
        for field, bad in (("case_item_id", None), ("case_item_id", 0),
                           ("case_well_id", None), ("case_well_id", 0),
                           ("case_item_id", 501.25), ("interpretation", None),
                           ("interpretation", "proven_toxin")):
            with self.subTest(field=field, bad=bad):
                state, okay, _ = rules.investigate(None, **dict(args, **{field: bad}))
                self.assertFalse(okay)
                self.assertEqual(state["records"], [])
        alternate, okay, reason = rules.investigate(
            None, **dict(args, interpretation="possible_exposure"))
        self.assertTrue(okay, reason)
        self.assertEqual(alternate["records"][0]["alternative"], "unrelated_illness")
        self.assertEqual(rules.normalize(json.loads(json.dumps(alternate))), alternate)
        for field, bad in (("case_item_id", None), ("case_item_id", 999.1),
                           ("case_well_id", None), ("case_well_id", 999.1),
                           ("alternative", "possible_exposure"),
                           ("interpretation", "proven_toxin")):
            forged = copy.deepcopy(alternate)
            forged["records"][0][field] = bad
            self.assertEqual(rules.normalize(forged)["records"], [])

    def test_well_origin_and_real_hidden_magnitude(self):
        # The original creator stamps the actual Village Square well ID.
        # An identically named object, a copied hidden tag, or an empty
        # mechanical value cannot become an authenticated case item.
        self.assertTrue(rules.well_case_source_valid(601, 601, 25))
        self.assertTrue(rules.well_case_source_valid(
            *json.loads(json.dumps([601, 601, 25]))))
        for origin, well, toxin in (
            (None, 601, 25), (0, 601, 25), (True, 601, 25),
            (602, 601, 25), (601, 602, 25), (601, None, 25),
            (601, 601, None), (601, 601, 0), (601, 601, -1),
            (601, 601, True), (601, 601, 25.0), (601, 601, "25"),
        ):
            with self.subTest(origin=origin, well=well, toxin=toxin):
                self.assertFalse(rules.well_case_source_valid(
                    origin, well, toxin))

    def test_multiple_real_case_specimens_select_stably(self):
        from itertools import permutations
        from types import SimpleNamespace

        room, detective = object(), object()
        def specimen(object_id, location, origin=601, toxin=25):
            return SimpleNamespace(id=object_id, location=location,
                                   origin=origin, toxin=toxin)

        floor_old = specimen(701, room)
        floor_new = specimen(702, room)
        carried = specimen(703, detective)
        decoy = specimen(1, detective, origin=602)
        no_toxin = specimen(2, detective, toxin=0)
        bad_id = specimen(True, detective)

        def real_clusters(objects):
            return [obj for obj in objects
                    if rules.well_case_source_valid(obj.origin, 601, obj.toxin)]

        # Two authentic clusters on the floor must no longer block inquiry.
        self.assertIs(rules.choose_case_item(
            real_clusters([floor_new, floor_old]), detective), floor_old)
        # An authentic carried specimen wins over room.contents order.
        for ordered in permutations((floor_new, carried, floor_old, decoy)):
            self.assertIs(rules.choose_case_item(
                real_clusters(ordered), detective), carried)
        # Among two carried specimens the lower stable physical ID wins.
        carried_old = specimen(699, detective)
        self.assertIs(rules.choose_case_item(
            real_clusters([carried, carried_old, floor_old]), detective),
            carried_old)
        # Forged origin, absent toxin and malformed IDs never win selection.
        self.assertIs(rules.choose_case_item(
            real_clusters([decoy, no_toxin, bad_id, floor_old]), detective),
            floor_old)
        self.assertIsNone(rules.choose_case_item(
            real_clusters([decoy, no_toxin, bad_id]), detective))
        self.assertIsNone(rules.choose_case_item([], detective))
        # A changed selection between preview and commit must be observable
        # by the adapter's existing atomic _case_item identity recheck.
        self.assertIsNot(rules.choose_case_item([carried], detective),
                         rules.choose_case_item([carried_old, carried], detective))

    def test_corrupt_public_records_fail_closed_without_crashing(self):
        for records in (17, True, "forged", {"event_id": 202}, object()):
            with self.subTest(records_type=type(records).__name__):
                raw = {"records": records}
                self.assertEqual(rules.normalize(raw)["records"], [])
                self.assertIn("requires signed source inspection",
                              rules.public_lines(raw, 1, lambda _id: None))


class WellCreationProvenance(unittest.TestCase):
    def test_registry_rejects_foreign_names_and_malformed_persistence(self):
        from collections import UserList
        self.assertTrue(rules.registered_well_growth(702, [702, 703]))
        self.assertTrue(rules.registered_well_growth(
            702, UserList(json.loads(json.dumps([702, 703])))))
        for raw in (None, "702", {"id": 702}, [True, "702"], [703],
                    [702.0], [0, -1], object()):
            with self.subTest(raw=repr(raw)):
                self.assertFalse(rules.registered_well_growth(702, raw))
        self.assertEqual(rules.well_growth_ids([703, 703, True, 0, 702]),
                         (703, 702))

    def test_actual_well_builder_never_promotes_same_key_foreign_object(self):
        # Compile the actual command helper, without importing the full
        # Evennia command module into the model-free rules test process.
        import ast
        import types
        from unittest.mock import patch

        source = (Path(__file__).resolve().parents[2]
                  / "spike/fvillage/commands/village_cmds.py").read_text()
        function = next(node for node in ast.parse(source).body
                        if isinstance(node, ast.FunctionDef)
                        and node.name == "ensure_well_mushrooms")
        code = compile(ast.Module(body=[function], type_ignores=[]),
                       "<actual ensure_well_mushrooms>", "exec")

        class Item:
            def __init__(self, number, key, location, tc):
                self.id, self.key, self.location, self.tc = (
                    number, key, location, tc)
                self.db = types.SimpleNamespace()
                self.alias_values = []
                self.aliases = types.SimpleNamespace(
                    all=lambda: list(self.alias_values),
                    add=lambda alias: self.alias_values.append(alias))
                self.tags = types.SimpleNamespace(add=lambda *_: None)
            def is_typeclass(self, path, exact=False):
                return exact and self.tc == path

        square = types.SimpleNamespace(key="Village Square", contents=[])
        well = Item(601, "well", square, "typeclasses.objects.VillageWell")
        foreign = Item(700, rules.CASE_ITEM_KEY, square,
                       "typeclasses.objects.Object")
        foreign.db.well_mushroom_source_id = 601  # Old vulnerable marker.
        foreign.db.mechanic_values = {"toxin": 25}
        square.contents.append(foreign)
        made = []
        def create_object(tc, key, location, aliases):
            item = Item(701 + len(made), key, location, tc)
            location.contents.append(item)
            made.append(item)
            return item
        def configure(obj, _visible, hidden_properties):
            obj.db.mechanic_values = dict(hidden_properties)

        utils = types.ModuleType("evennia.utils")
        utils.create = types.SimpleNamespace(create_object=create_object)
        utils.search = types.SimpleNamespace(
            search_object=lambda _name: [well])
        evennia = types.ModuleType("evennia")
        evennia.utils = utils
        namespace = {
            "WELL_MUSHROOMS_DESC": "Well growth",
            "WELL_MUSHROOMS_CONSUME": {"nourish": 1, "toxic": 25},
            "configure_mechanical_properties": configure,
        }
        with patch.dict(sys.modules, {"evennia": evennia,
                                      "evennia.utils": utils}):
            exec(code, namespace)
            ensure = namespace["ensure_well_mushrooms"]
            grown = ensure()
            self.assertIs(grown, made[0])
            self.assertIsNot(grown, foreign)
            self.assertEqual(foreign.db.well_mushroom_source_id, 601)
            self.assertFalse(rules.registered_well_growth(
                foreign.id, well.db.well_mushroom_spawn_ids))
            self.assertTrue(rules.registered_well_growth(
                grown.id, well.db.well_mushroom_spawn_ids))
            self.assertIs(ensure(), grown)  # No duplicate on rebuild.
            self.assertEqual(len(made), 1)

            # Physically carried first growth remains signed after regrowth.
            square.contents.remove(grown)
            grown.location = object()
            second = ensure()
            self.assertIs(second, made[1])
            self.assertEqual(well.db.well_mushroom_spawn_ids, [701, 702])
            self.assertTrue(rules.registered_well_growth(
                grown.id, well.db.well_mushroom_spawn_ids))
            self.assertIs(ensure(), second)

            # Restart-like JSON persistence retains registry and same item.
            well.db.well_mushroom_spawn_ids = json.loads(json.dumps(
                well.db.well_mushroom_spawn_ids))
            self.assertIs(ensure(), second)
            self.assertEqual(len(made), 2)

            # Ambiguous canonical wells fail closed, not a name fallback.
            utils.search.search_object = lambda _name: [well, well]
            self.assertIsNone(ensure())
            self.assertEqual(len(made), 2)


if __name__ == "__main__":
    unittest.main()
