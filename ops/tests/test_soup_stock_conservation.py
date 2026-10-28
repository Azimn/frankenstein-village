"""Signed soup work conserves live stock under late competing actions.

Execute exact production functions with Evennia boundaries substituted and
change canonical stock after the command preview but before the signed event.
These are deterministic interleavings, NOT parallel Evennia execution.
"""
import ast
import copy
from contextlib import nullcontext
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spike" / "fvillage"))
from world import soup_state


class FakeItem:
    def __init__(self, owner, identifier):
        self.id = identifier
        self.location = owner
        self.db = SimpleNamespace()
        self.tags = SimpleNamespace(add=lambda _tag: None)
        self.deleted = False

    def delete(self):
        self.deleted = True
        self.location = None


class SoupStockConservationTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / "spike" / "fvillage" / "world" / "soup_kitchen.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {"prep", "simmer", "procure", "deliver"}
        functions = [
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name in names
        ]
        self.assertEqual({f.name for f in functions}, names)
        module = ast.fix_missing_locations(
            ast.Module(body=functions, type_ignores=[]))
        self.api = {}
        exec(compile(module, str(path), "exec"), self.api)

        self.day = 1
        self.hour = 21
        self.warm = False
        self.tavern = SimpleNamespace(
            id=11, key="The Blood of the Vine",
            db=SimpleNamespace(soup_pantry=soup_state.pantry(None, 1),
                               civic_hearth=None))
        self.market = SimpleNamespace(
            id=12, key="Market Lane",
            db=SimpleNamespace(soup_market=soup_state.market_source(None, 1)))
        self.mask = SimpleNamespace(
            id=301, key="KitchenTester", role="innkeep",
            account=SimpleNamespace(id=400), location=self.tavern,
            contents=[], db=SimpleNamespace(soup_notebook=None))
        self.created = []
        self.recorded = []
        self.events = []
        self.ledger = {}
        self.before_consequence = lambda: None

        def create_object(typeclass, *, key, location, aliases):
            item = FakeItem(location, 500 + len(self.created))
            item.key = key
            item.aliases = aliases
            location.contents.append(item)
            self.created.append(item)
            return item

        def publish(kind, *, actor, payload, consequence):
            self.assertIs(actor, self.mask)
            self.before_consequence()
            event = {"id": 100 + len(self.events), "kind": kind,
                     "payload": payload, "status": "recorded",
                     "actor": {"mask_id": actor.id,
                               "account_id": actor.account.id}}
            event["consequence"] = consequence(event)
            event["status"] = "complete"
            self.events.append(event)
            self.ledger[event["id"]] = event
            return event

        def access(actor, room_key):
            target = (self.tavern if room_key == "The Blood of the Vine"
                      else self.market)
            if actor.location is not target:
                return None, "Not at the required workplace."
            return target, None

        self.api.update({
            "_access": access,
            "_held": lambda actor, attribute: [
                item for item in actor.contents if item.location is actor
                and getattr(item.db, attribute, None)
            ],
            "_clock": lambda: (self.day, self.hour),
            "_room": lambda name: (
                self.market if name == self.market.key else
                self.tavern if name == self.tavern.key else None
            ),
            "_full_bowls": lambda actor: sum(
                1 for item in actor.contents if item.location is actor
                and (getattr(item.db, "soup_serving", None)
                     or getattr(item.db, "kitchen_ration", None))
                and getattr(item.db, "servings", 0) > 0),
            "hearth_state": SimpleNamespace(active=lambda *_args: self.warm),
            "active_calling": lambda actor: actor.role,
            "record_participation": lambda actor, activity, calling: (
                self.recorded.append((activity, calling))
            ),
            "transaction": SimpleNamespace(atomic=nullcontext),
            "create_object": create_object,
            "publish_world_event": publish,
            "get_event_ledger": lambda: SimpleNamespace(
                get_event=lambda event_id: self.ledger.get(event_id)),
            "soup_state": soup_state,
            "copy": copy,
            "TAVERN": self.tavern.key,
            "MARKET": self.market.key,
            "PACKET": "a packet of soup ingredients",
            "CRATE": "a crate of kitchen roots",
        })

    def execute(self, name, *args):
        return self.api[name](self.mask, *args)

    def crate(self):
        item = FakeItem(self.mask, 480 + len(self.mask.contents))
        item.db.soup_delivery = {
            "day": 1, "market_id": self.market.id,
            "procurement_event_id": 78, "merchant_id": 302,
        }
        self.mask.contents.append(item)
        self.ledger[78] = {
            "id": 78, "kind": "professional.merchant_kitchen_procurement",
            "status": "complete", "actor": {"mask_id": 302, "account_id": 400},
            "payload": {"day": 1, "market_room_id": self.market.id},
            "consequence": {"crate_id": item.id},
        }
        return item

    def test_prep_competing_ingredient_depletion_preserves_real_stock(self):
        state = soup_state.pantry(None, 1)
        state["stock"]["thyme"] = 1
        self.tavern.db.soup_pantry = state

        def competitor():
            current, ok, reason = soup_state.reserve(
                self.tavern.db.soup_pantry, 1, "turnip", "thyme")
            self.assertTrue(ok, reason)
            self.tavern.db.soup_pantry = current

        self.before_consequence = competitor
        result, error = self.execute("prep", "turnip", "thyme")
        self.assertIsNone(result)
        self.assertIn("lacks", error)
        self.assertEqual(self.tavern.db.soup_pantry["stock"]["thyme"], 0)
        self.assertEqual(self.created, [])
        self.assertEqual(self.recorded, [])

    def test_prep_receipt_and_packet_derive_from_latest_pantry(self):
        def competitor():
            current, ok, reason = soup_state.reserve(
                self.tavern.db.soup_pantry, 1, "turnip", "thyme")
            self.assertTrue(ok, reason)
            self.tavern.db.soup_pantry = current

        self.before_consequence = competitor
        result, error = self.execute("prep", "turnip", "thyme")
        self.assertIsNone(error)
        self.assertEqual(result["stock"]["turnip"], 1)
        self.assertEqual(result["stock"]["thyme"], 0)
        self.assertEqual(self.tavern.db.soup_pantry["stock"], result["stock"])
        self.assertEqual(self.created[0].db.soup_preparation["prep_event_id"], 100)
        self.assertEqual(len(self.recorded), 1)

    def test_prep_interposed_packet_and_day_change_are_rejected(self):
        def competitor():
            extra = FakeItem(self.mask, 900)
            extra.db.soup_preparation = {"other": True}
            self.mask.contents.append(extra)

        self.before_consequence = competitor
        result, error = self.execute("prep", "turnip", "salt")
        self.assertIsNone(result)
        self.assertIn("already carry", error.lower())
        self.assertEqual(self.tavern.db.soup_pantry["stock"]["turnip"], 3)
        self.assertEqual(self.created, [])

        self.before_consequence = lambda: setattr(self, "day", 2)
        self.mask.contents.clear()
        result, error = self.execute("prep", "turnip", "salt")
        self.assertIsNone(result)
        self.assertIn("day changed", error.lower())

    def test_procure_last_market_crate_cannot_be_duplicated(self):
        self.mask.location = self.market
        self.mask.role = "merchant"
        self.market.db.soup_market["remaining"] = 1

        def competitor():
            state, accepted = soup_state.issue_crate(
                self.market.db.soup_market, 1)
            self.assertTrue(accepted)
            self.market.db.soup_market = state

        self.before_consequence = competitor
        result, error = self.execute("procure")
        self.assertIsNone(result)
        self.assertIn("no more", error.lower())
        self.assertEqual(self.market.db.soup_market["remaining"], 0)
        self.assertEqual(self.created, [])
        self.assertEqual(self.recorded, [])

    def test_procure_receipt_uses_live_stock_after_other_merchant(self):
        self.mask.location = self.market
        self.mask.role = "merchant"

        def competitor():
            state, accepted = soup_state.issue_crate(
                self.market.db.soup_market, 1)
            self.assertTrue(accepted)
            self.market.db.soup_market = state

        self.before_consequence = competitor
        result, error = self.execute("procure")
        self.assertIsNone(error)
        self.assertEqual(result["remaining"], 0)
        self.assertEqual(self.market.db.soup_market["remaining"], 0)
        self.assertEqual(self.created[0].db.soup_delivery["procurement_event_id"], 100)

    def test_procure_received_crate_during_work_is_rejected(self):
        self.mask.location = self.market
        self.mask.role = "merchant"
        self.before_consequence = self.crate
        result, error = self.execute("procure")
        self.assertIsNone(result)
        self.assertIn("already carry", error.lower())
        self.assertEqual(self.market.db.soup_market["remaining"], 2)
        self.assertEqual(self.created, [])

    def test_deliver_requires_a_real_market_procurement_receipt(self):
        valid = {
            "day": 1, "market_id": self.market.id,
            "procurement_event_id": 78, "merchant_id": 302,
        }
        invalid = (
            {"day": 1},
            {**valid, "market_id": self.tavern.id},
            {**valid, "procurement_event_id": True},
            {**valid, "merchant_id": 0},
            {**valid, "day": "1"},
            object(),
        )
        for source in invalid:
            with self.subTest(source=repr(source)):
                self.mask.contents.clear()
                crate = self.crate()
                crate.db.soup_delivery = source
                before = copy.deepcopy(self.tavern.db.soup_pantry)
                result, error = self.execute("deliver")
                self.assertIsNone(result)
                self.assertIn("valid signed market procurement", error)
                self.assertEqual(self.tavern.db.soup_pantry, before)
                self.assertFalse(crate.deleted)
                self.assertIs(crate.location, self.mask)
                self.assertEqual(self.events, [])

    def test_delivery_rejects_plausible_but_unsigned_market_crate(self):
        for field, value in (
            ("kind", "village.kitchen_delivery"),
            ("status", "consequence_failed"),
            ("actor", {"mask_id": 999}),
            ("payload", {"day": 2, "market_room_id": self.market.id}),
            ("consequence", {"crate_id": 999}),
        ):
            with self.subTest(field=field):
                self.mask.contents.clear()
                crate = self.crate()
                self.ledger[78][field] = value
                before = copy.deepcopy(self.tavern.db.soup_pantry)
                result, error = self.execute("deliver")
                self.assertIsNone(result)
                self.assertIn("completed Merchant procurement", error)
                self.assertEqual(self.tavern.db.soup_pantry, before)
                self.assertFalse(crate.deleted)
                self.assertEqual(self.events, [])

        self.mask.contents.clear()
        crate = self.crate()
        del self.ledger[78]
        result, error = self.execute("deliver")
        self.assertIsNone(result)
        self.assertIn("completed Merchant procurement", error)
        self.assertFalse(crate.deleted)
        self.assertEqual(self.events, [])

    def test_delivery_rechecks_signed_source_at_commit(self):
        crate = self.crate()
        self.before_consequence = lambda: self.ledger[78].update(
            {"status": "consequence_failed"})
        result, error = self.execute("deliver")
        self.assertIsNone(result)
        self.assertIn("signed procurement changed", error)
        self.assertFalse(crate.deleted)
        self.assertEqual(self.tavern.db.soup_pantry["stock"]["turnip"], 3)
        self.assertEqual(self.events, [])

    def test_real_merchant_crate_can_be_delivered_by_a_courier(self):
        self.mask.location = self.market
        self.mask.role = "merchant"
        result, error = self.execute("procure")
        self.assertIsNone(error)
        self.assertIsNotNone(result)
        crate = self.created[0]
        self.assertEqual(crate.db.soup_delivery["market_id"], self.market.id)
        self.mask.location = self.tavern
        self.mask.role = "wanderer"
        result, error = self.execute("deliver")
        self.assertIsNone(error)
        self.assertEqual(result["turnips"], 5)
        self.assertTrue(crate.deleted)
        self.assertEqual(len(self.events), 2)

    def test_deliver_full_pantry_after_preview_preserves_crate(self):
        self.tavern.db.soup_pantry["stock"]["turnip"] = 5
        crate = self.crate()

        def competitor():
            updated, accepted = soup_state.deliver(
                self.tavern.db.soup_pantry, 1)
            self.assertTrue(accepted)
            self.tavern.db.soup_pantry = updated

        self.before_consequence = competitor
        result, error = self.execute("deliver")
        self.assertIsNone(result)
        self.assertIn("keep the crate", error.lower())
        self.assertEqual(self.tavern.db.soup_pantry["stock"]["turnip"], 7)
        self.assertFalse(crate.deleted)
        self.assertIs(crate.location, self.mask)

    def test_deliver_after_other_cook_uses_current_stock(self):
        crate = self.crate()

        def competitor():
            updated, ok, reason = soup_state.reserve(
                self.tavern.db.soup_pantry, 1, "turnip", "thyme")
            self.assertTrue(ok, reason)
            self.tavern.db.soup_pantry = updated

        self.before_consequence = competitor
        result, error = self.execute("deliver")
        self.assertIsNone(error)
        self.assertEqual(result["turnips"], 4)
        self.assertEqual(self.events[0]["consequence"]["turnip_stock"], 4)
        self.assertEqual(self.tavern.db.soup_pantry["stock"]["turnip"], 4)
        self.assertTrue(crate.deleted)

    def test_deliver_moved_or_altered_crate_does_not_add_stock(self):
        crate = self.crate()
        self.before_consequence = lambda: setattr(crate, "location", self.market)
        result, error = self.execute("deliver")
        self.assertIsNone(result)
        self.assertIn("changed hands", error)
        self.assertEqual(self.tavern.db.soup_pantry["stock"]["turnip"], 3)
        self.assertFalse(crate.deleted)

        crate.location = self.mask
        self.before_consequence = lambda: crate.db.soup_delivery.update(
            {"procurement_event_id": 999})
        result, error = self.execute("deliver")
        self.assertIsNone(result)
        self.assertIn("changed hands", error)
        self.assertEqual(self.tavern.db.soup_pantry["stock"]["turnip"], 3)

    def test_deliver_rejects_clock_change_without_consuming_crate(self):
        crate = self.crate()
        self.before_consequence = lambda: setattr(self, "day", 2)
        result, error = self.execute("deliver")
        self.assertIsNone(result)
        self.assertIn("day changed", error.lower())
        self.assertFalse(crate.deleted)
        self.assertEqual(self.tavern.db.soup_pantry["stock"]["turnip"], 3)


    def test_simmer_consumes_one_packet_and_signs_one_real_bowl(self):
        prepared, error = self.execute("prep", "turnip", "thyme")
        self.assertIsNone(error)
        packet = self.created[0]
        self.warm = True
        cooked, error = self.execute("simmer")
        self.assertIsNone(error)
        self.assertTrue(packet.deleted)
        self.assertEqual(len(self.created), 2)
        bowl = self.created[1]
        self.assertIs(bowl.location, self.mask)
        self.assertEqual(bowl.db.soup_serving["prep_event_id"],
                         prepared["event_id"])
        self.assertEqual(bowl.db.soup_serving["quality"], cooked["quality"])
        self.assertTrue(cooked["warmed"])
        self.assertEqual(
            self.tavern.db.soup_pantry["history"][-1]["cook_event_id"],
            cooked["event_id"])
        self.assertEqual(self.mask.db.soup_notebook[-1]["cook_event_id"],
                         cooked["event_id"])
        self.assertEqual(self.recorded[-1],
                         ("soup_batches_cooked", "innkeep"))

    def test_simmer_interposed_packet_transfer_does_not_mint_bowl(self):
        self.execute("prep", "turnip", "salt")
        packet = self.created[0]
        self.before_consequence = lambda: setattr(packet, "location", self.market)
        cooked, error = self.execute("simmer")
        self.assertIsNone(cooked)
        self.assertIn("moved, changed or consumed", error)
        self.assertEqual(len(self.created), 1)
        self.assertFalse(packet.deleted)
        self.assertEqual(len(self.events), 1)
        self.assertFalse(self.tavern.db.soup_pantry["history"])
        self.assertIsNone(self.mask.db.soup_notebook)

    def test_simmer_rechecks_role_clock_packet_and_bowl_limit(self):
        self.execute("prep", "barley", "salt")
        packet = self.created[0]

        self.before_consequence = lambda: setattr(self.mask, "role", "merchant")
        cooked, error = self.execute("simmer")
        self.assertIsNone(cooked)
        self.assertIn("active Innkeep", error)
        self.mask.role = "innkeep"

        self.before_consequence = lambda: setattr(self, "hour", 22)
        cooked, error = self.execute("simmer")
        self.assertIsNone(cooked)
        self.assertIn("clock changed", error)
        self.hour = 21

        self.before_consequence = lambda: packet.db.soup_preparation.update(
            {"prep_event_id": 999})
        cooked, error = self.execute("simmer")
        self.assertIsNone(cooked)
        self.assertIn("changed or consumed", error)
        packet.db.soup_preparation["prep_event_id"] = 100

        def other_bowls():
            for index in range(3):
                bowl = FakeItem(self.mask, 700 + index)
                bowl.db.soup_serving = {"event_id": 500 + index}
                bowl.db.servings = 1
                self.mask.contents.append(bowl)

        self.before_consequence = other_bowls
        cooked, error = self.execute("simmer")
        self.assertIsNone(cooked)
        self.assertIn("three soup bowls", error)
        self.assertFalse(packet.deleted)
        self.assertEqual(len(self.created), 1)
        self.assertEqual(len(self.events), 1)
        self.assertFalse(self.tavern.db.soup_pantry["history"])
        self.assertIsNone(self.mask.db.soup_notebook)


    def test_prep_rejects_hour_rollover_without_minting_packet(self):
        before = copy.deepcopy(self.tavern.db.soup_pantry)
        self.before_consequence = lambda: setattr(self, "hour", 22)
        result, error = self.execute("prep", "turnip", "thyme")
        self.assertIsNone(result)
        self.assertIn("hour changed", error.lower())
        self.assertEqual(self.tavern.db.soup_pantry, before)
        self.assertEqual(self.created, [])
        self.assertEqual(self.events, [])
        self.assertEqual(self.recorded, [])

    def test_procure_rejects_hour_rollover_without_spending_market_stock(self):
        self.mask.location = self.market
        self.mask.role = "merchant"
        before = copy.deepcopy(self.market.db.soup_market)
        self.before_consequence = lambda: setattr(self, "hour", 22)
        result, error = self.execute("procure")
        self.assertIsNone(result)
        self.assertIn("hour changed", error.lower())
        self.assertEqual(self.market.db.soup_market, before)
        self.assertEqual(self.created, [])
        self.assertEqual(self.events, [])
        self.assertEqual(self.recorded, [])

    def test_deliver_rejects_hour_rollover_without_consuming_crate(self):
        crate = self.crate()
        before = copy.deepcopy(self.tavern.db.soup_pantry)
        self.before_consequence = lambda: setattr(self, "hour", 22)
        result, error = self.execute("deliver")
        self.assertIsNone(result)
        self.assertIn("hour changed", error.lower())
        self.assertEqual(self.tavern.db.soup_pantry, before)
        self.assertFalse(crate.deleted)
        self.assertIs(crate.location, self.mask)
        self.assertEqual(self.events, [])


    def test_prep_account_swap_cannot_sign_or_spend_stock(self):
        before = copy.deepcopy(self.tavern.db.soup_pantry)
        self.before_consequence = lambda: setattr(
            self.mask, "account", SimpleNamespace(id=401))
        result, error = self.execute("prep", "turnip", "thyme")
        self.assertIsNone(result)
        self.assertIn("account identity changed", error)
        self.assertEqual(self.tavern.db.soup_pantry, before)
        self.assertEqual(self.created, [])
        self.assertEqual(self.events, [])
        self.assertEqual(self.recorded, [])

    def test_simmer_account_swap_preserves_real_packet(self):
        prepared, error = self.execute("prep", "barley", "salt")
        self.assertIsNone(error)
        packet = self.created[0]
        self.before_consequence = lambda: setattr(
            self.mask, "account", SimpleNamespace(id=401))
        result, error = self.execute("simmer")
        self.assertIsNone(result)
        self.assertIn("account identity changed", error)
        self.assertFalse(packet.deleted)
        self.assertEqual(len(self.created), 1)
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.tavern.db.soup_pantry["history"], [])
        self.assertIsNone(self.mask.db.soup_notebook)

    def test_procure_account_swap_does_not_issue_market_crate(self):
        self.mask.location = self.market
        self.mask.role = "merchant"
        before = copy.deepcopy(self.market.db.soup_market)
        self.before_consequence = lambda: setattr(
            self.mask, "account", SimpleNamespace(id=401))
        result, error = self.execute("procure")
        self.assertIsNone(result)
        self.assertIn("account identity changed", error)
        self.assertEqual(self.market.db.soup_market, before)
        self.assertEqual(self.created, [])
        self.assertEqual(self.events, [])

    def test_deliver_account_swap_preserves_physical_crate(self):
        crate = self.crate()
        before = copy.deepcopy(self.tavern.db.soup_pantry)
        self.before_consequence = lambda: setattr(
            self.mask, "account", SimpleNamespace(id=401))
        result, error = self.execute("deliver")
        self.assertIsNone(result)
        self.assertIn("account identity changed", error)
        self.assertEqual(self.tavern.db.soup_pantry, before)
        self.assertFalse(crate.deleted)
        self.assertIs(crate.location, self.mask)
        self.assertEqual(self.events, [])


if __name__ == "__main__":
    unittest.main()
