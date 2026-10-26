"""Regression for the authoritative reserve count in commission delivery receipts.

Execute the real civic_work.deliver function with its Evennia boundaries
substituted, including a competing legitimate hearth delivery after the
command preview but before its signed event consequence.
"""
import ast
from contextlib import nullcontext
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spike" / "fvillage"))
from world import civic_commissions, hearth_state


class FakeBundle:
    def __init__(self, owner):
        self.id = 450
        self.location = owner
        self.db = SimpleNamespace(civic_firewood=True)
        self.deleted = False

    def delete(self):
        self.deleted = True


class CivicDeliveryReceiptTests(unittest.TestCase):
    def test_delivery_reports_committed_rack_not_stale_preview(self):
        source_path = ROOT / "spike" / "fvillage" / "world" / "civic_work.py"
        parsed = ast.parse(source_path.read_text(encoding="utf-8"))
        function = next(
            node for node in parsed.body
            if isinstance(node, ast.FunctionDef) and node.name == "deliver"
        )
        # The exact production function is executed, not a copied algorithm.
        isolated = ast.fix_missing_locations(
            ast.Module(body=[function], type_ignores=[])
        )
        namespace = {}
        exec(compile(isolated, str(source_path), "exec"), namespace)

        supplier_state = civic_commissions.refresh(None, 1)
        supplier_state, accepted, reason = civic_commissions.pledge(
            supplier_state, 1, 101, "Supplier", bundle_id=450, event_id=10
        )
        self.assertTrue(accepted, reason)
        mask = SimpleNamespace(account=SimpleNamespace(id=202), key="Carrier")
        bundle = FakeBundle(mask)
        tavern = SimpleNamespace(db=SimpleNamespace(
            civic_commission=supplier_state,
            civic_hearth={"reserve": 1},
        ))
        events = []

        def publish(kind, *, actor, payload, consequence):
            self.assertEqual(kind, "civic.commission_completed")
            self.assertIs(actor, mask)
            # Another ordinary delivery commits after this command's
            # preview. The signed commission must report its actual count.
            rack, accepted = hearth_state.deliver(tavern.db.civic_hearth)
            self.assertTrue(accepted)
            tavern.db.civic_hearth = rack
            event = {"id": 11}
            event["consequence"] = consequence(event)
            events.append(event)
            return event

        namespace.update({
            "_guard": lambda actor, room: None,
            "_tavern": lambda: tavern,
            "_clock": lambda: (1, 21),
            "_state": lambda obj, day: civic_commissions.refresh(
                obj.db.civic_commission, day
            ),
            "_carried": lambda actor: [bundle],
            "TAVERN_KEY": "The Blood of the Vine",
            "hearth_state": hearth_state,
            "civic_commissions": civic_commissions,
            "transaction": SimpleNamespace(atomic=nullcontext),
            "publish_world_event": publish,
        })
        receipt, error = namespace["deliver"](mask)
        self.assertIsNone(error)
        self.assertEqual(tavern.db.civic_hearth["reserve"], 3)
        self.assertEqual(events[0]["consequence"]["reserve"], 3)
        self.assertEqual(receipt["reserve"], 3)
        self.assertEqual(receipt["event_id"], 11)
        self.assertTrue(bundle.deleted)
        self.assertEqual(tavern.db.civic_commission["commission"]["status"], "complete")
        self.assertEqual(tavern.db.civic_commission["commission"]["event_ids"], [10, 11])
        self.assertEqual(len(tavern.db.civic_commission["history"]), 1)


if __name__ == "__main__":
    unittest.main()
