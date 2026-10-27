"""Exercise production public-brazier action with real stock interleavings.

The game action functions are executed from their AST with Evennia boundary
calls mocked. Interleaving tests do NOT establish truly simultaneous SQL
transactions. Real-client and restart tests live in spike/tests.
"""
import ast
from contextlib import nullcontext
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spike/fvillage"))
from world import square_brazier_state as fire


class FakeBundle:
    def __init__(self, owner, key=100):
        self.id = key
        self.key = "a bundle of firewood"
        self.location = owner
        self.db = SimpleNamespace(
            civic_firewood=True, gather_event_id=200 + key, source_day=1
        )
        self.deleted = False

    def delete(self):
        self.deleted = True
        self.location = None


class SquareBrazierRuntimeTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / "spike/fvillage/world/square_brazier.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        functions = [
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name in {"_verified_gather", "act"}
        ]
        self.assertEqual({node.name for node in functions},
                         {"_verified_gather", "act"})
        module = ast.fix_missing_locations(
            ast.Module(body=functions, type_ignores=[])
        )
        self.ns = {}
        exec(compile(module, str(path), "exec"), self.ns)
        self.day, self.hour = 1, 21
        self.square = SimpleNamespace(key="Village Square")
        self.mask = SimpleNamespace(
            key="Traveler", id=31, account=SimpleNamespace(id=22),
            location=self.square
        )
        self.brazier = SimpleNamespace(
            id=50, location=self.square,
            db=SimpleNamespace(square_brazier=None)
        )
        self.bundle = FakeBundle(self.mask)
        self.pledged = None
        self.before_consequence = lambda: None
        self.events = []
        self.source = {
            "id": self.bundle.db.gather_event_id,
            "kind": "civic.hearth_firewood_gathered", "status": "complete",
            "actor": {"mask_id": self.mask.id, "account_id": self.mask.account.id},
            "payload": {"resource": "a bundle of firewood",
                        "day": 1, "hour": 20},
            "consequence": {"bundle_id": self.bundle.id,
                            "woodpile_object_id": 19},
        }

        class MissingSource(Exception):
            pass

        class LedgerObjects:
            def get(_self, *, db_key):
                assert db_key == "world_event_ledger"
                return SimpleNamespace(get_event=lambda event_id: (
                    self.source if self.source
                    and self.source["id"] == event_id else None
                ))

        self.scriptdb = SimpleNamespace(
            DoesNotExist=MissingSource, objects=LedgerObjects()
        )

        def publish(kind, *, actor, payload, consequence):
            self.assertTrue(kind.startswith("civic.square_brazier_"))
            self.assertIs(actor, self.mask)
            self.before_consequence()
            event = {"id": 90 + len(self.events), "kind": kind,
                     "payload": payload}
            event["consequence"] = consequence(event)
            self.events.append(event)
            return event

        self.ns.update({
            "_guard": lambda player: (
                (self.square, None) if player.location is self.square
                else (None, "Not in Village Square.")
            ),
            "_brazier": lambda: self.brazier,
            "_clock": lambda: (self.day, self.hour),
            "_usable_bundle": lambda player, day: (
                self.bundle
                if self.bundle.location is player
                and self.bundle.id != self.pledged
                else None
            ),
            "_carried": lambda player: (
                [self.bundle] if self.bundle.location is player else []
            ),
            "_pledged_bundle_id": lambda day: self.pledged,
            "square_brazier_state": fire,
            "transaction": SimpleNamespace(atomic=nullcontext),
            "publish_world_event": publish,
            "ScriptDB": self.scriptdb,
            "FIREWOOD_KEY": "a bundle of firewood",
        })

    def act(self, mode):
        return self.ns["act"](self.mask, mode)

    def test_signed_light_spends_one_actual_bundle_and_records_provenance(self):
        result, error = self.act("light")
        self.assertIsNone(error)
        self.assertTrue(self.bundle.deleted)
        self.assertEqual(result["remaining"], fire.LIGHT_HOURS)
        receipt = self.events[0]["consequence"]
        self.assertEqual(receipt["bundle_id"], self.bundle.id)
        self.assertEqual(receipt["gather_event_id"],
                         self.bundle.db.gather_event_id)
        self.assertEqual(len(self.brazier.db.square_brazier["history"]), 1)
        self.assertEqual(self.events[0]["kind"], "civic.square_brazier_light")

    def test_competing_visitor_lights_first_and_bundle_is_retained(self):
        def competitor():
            new_state, okay, reason = fire.contribute(
                self.brazier.db.square_brazier, 1, 21, mode="light",
                actor={"mask_id": 49, "mask": "Earlier Traveler"},
                bundle_id=75, gather_event_id=177, event_id=77
            )
            self.assertTrue(okay, reason)
            self.brazier.db.square_brazier = new_state

        self.before_consequence = competitor
        result, error = self.act("light")
        self.assertIsNone(result)
        self.assertIn("already burning", error)
        self.assertFalse(self.bundle.deleted)
        self.assertIs(self.bundle.location, self.mask)
        self.assertEqual(len(self.brazier.db.square_brazier["history"]), 1)

    def test_moved_bundle_before_consequence_is_never_consumed(self):
        self.before_consequence = lambda: setattr(
            self.bundle, "location", object()
        )
        result, error = self.act("light")
        self.assertIsNone(result)
        self.assertIn("no longer in your hands", error)
        self.assertFalse(self.bundle.deleted)
        self.assertIsNone(self.brazier.db.square_brazier)

    def test_newly_pledged_bundle_is_protected_during_event(self):
        self.before_consequence = lambda: setattr(
            self, "pledged", self.bundle.id
        )
        result, error = self.act("light")
        self.assertIsNone(result)
        self.assertIn("pledged to a civic commission", error)
        self.assertFalse(self.bundle.deleted)
        self.assertIsNone(self.brazier.db.square_brazier)

    def test_clock_changing_mid_action_does_not_steal_fuel(self):
        self.before_consequence = lambda: setattr(self, "hour", 22)
        result, error = self.act("light")
        self.assertIsNone(result)
        self.assertIn("clock changed", error)
        self.assertFalse(self.bundle.deleted)

    def test_missing_or_forged_gathering_never_creates_public_warmth(self):
        cases = (
            ("missing event", None),
            ("failed source", {"status": "consequence_failed"}),
            ("wrong kind", {"kind": "civic.hearth_tended"}),
            ("wrong bundle", {"consequence": {
                "bundle_id": 500, "woodpile_object_id": 19,
            }}),
            ("wrong source day", {"payload": {
                "resource": "a bundle of firewood", "day": 2, "hour": 20,
            }}),
            ("wrong material", {"payload": {
                "resource": "a kitchen crate", "day": 1, "hour": 20,
            }}),
            ("anonymous source", {"actor": {
                "mask_id": None, "account_id": 22,
            }}),
        )
        baseline = dict(self.source)
        for label, mutation in cases:
            with self.subTest(label=label):
                self.source = None if mutation is None else {
                    **baseline, **mutation
                }
                result, error = self.act("light")
                self.assertIsNone(result)
                self.assertIn("completed matching Square gathering", error)
                self.assertFalse(self.bundle.deleted)
                self.assertIsNone(self.brazier.db.square_brazier)
                self.assertFalse(self.events)
        self.source = baseline

    def test_misdated_bundle_and_malformed_source_id_do_not_burn(self):
        self.bundle.db.source_day = 2
        result, error = self.act("light")
        self.assertIsNone(result)
        self.assertIn("gathering", error)
        self.bundle.db.source_day = 1
        self.bundle.db.gather_event_id = True
        result, error = self.act("light")
        self.assertIsNone(result)
        self.assertIn("gathering", error)
        self.assertFalse(self.bundle.deleted)

    def test_source_revoked_between_preview_and_commit_preserves_bundle(self):
        self.before_consequence = lambda: self.source.update(
            status="consequence_failed"
        )
        result, error = self.act("light")
        self.assertIsNone(result)
        self.assertIn("receipt changed", error)
        self.assertFalse(self.bundle.deleted)
        self.assertIsNone(self.brazier.db.square_brazier)

    def test_bundle_transfer_keeps_original_source_authority(self):
        # A legitimately gathered bundle may pass to a different player.
        self.source["actor"] = {"mask_id": 777, "account_id": 888}
        result, error = self.act("light")
        self.assertIsNone(error)
        self.assertTrue(self.bundle.deleted)
        self.assertEqual(result["remaining"], fire.LIGHT_HOURS)

    def test_feed_of_cold_fire_and_second_light_are_refused(self):
        result, error = self.act("feed")
        self.assertIsNone(result)
        self.assertIn("cold", error)
        self.assertFalse(self.bundle.deleted)
        self.assertEqual(self.events, [])

    def test_refuse_over_full_horizon_with_custody_intact(self):
        self.brazier.db.square_brazier = {
            "warm_until": fire.hour_index(1, 21) + 10,
            "last_action_at": fire.hour_index(1, 21),
            "history": [],
        }
        result, error = self.act("feed")
        self.assertIsNone(result)
        self.assertIn("well supplied", error)
        self.assertFalse(self.bundle.deleted)


if __name__ == "__main__":
    unittest.main()
