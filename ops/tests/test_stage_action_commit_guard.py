"""Exercise real stage command consequences after preflight state changes.

The production act() function is loaded from its AST so these tests do not
need an Evennia server. The clean-checkout regression separately exercises
real accounts and server restart. No simulated concurrency is called a lock.
"""
import ast
from contextlib import nullcontext
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spike" / "fvillage"))
from world import stage_state


class StageActionCommitGuardTests(unittest.TestCase):
    def setUp(self):
        self.clock = [1, 20]
        self.tavern = SimpleNamespace(
            id=55, key="The Blood of the Vine",
            db=SimpleNamespace(village_stage=None), contents=[],
        )
        self.performer = self.player(7, 70, "Musician", "performer")
        self.listener = self.player(8, 80, "Listener", "merchant")
        self.tavern.contents = [self.performer, self.listener]
        self.before_commit = lambda: None
        self.participation = []
        self.next_event = 100

        path = ROOT / "spike" / "fvillage" / "world" / "stage_work.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        funcs = [
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "act"
        ]
        self.assertEqual(len(funcs), 1)

        def guard(mask):
            if mask.account is None or mask.location is not self.tavern:
                return self.tavern, "Visit the real stage at the Blood of the Vine."
            return self.tavern, None

        def publish(kind, *, actor, payload, consequence):
            self.next_event += 1
            self.before_commit()
            receipt = consequence({"id": self.next_event})
            return {"id": self.next_event, "consequence": receipt}

        namespace = {
            "_guard": guard,
            "_clock": lambda: tuple(self.clock),
            "stage_state": stage_state,
            "active_calling": lambda mask: mask.calling,
            "transaction": SimpleNamespace(atomic=nullcontext),
            "publish_world_event": publish,
            "record_participation": lambda *args, **kwargs: self.participation.append(
                (args, kwargs)
            ),
        }
        exec(compile(ast.fix_missing_locations(
            ast.Module(body=funcs, type_ignores=[])), str(path), "exec"),
            namespace)
        self.act = namespace["act"]

    def player(self, account_id, mask_id, name, calling):
        account = SimpleNamespace(
            id=account_id, sessions=SimpleNamespace(all=lambda: [object()])
        )
        return SimpleNamespace(
            id=mask_id, key=name, account=account, calling=calling,
            location=self.tavern,
        )

    def test_departed_performer_cannot_sign_rehearsal(self):
        self.before_commit = lambda: setattr(self.performer, "location", None)
        result, error = self.act(self.performer, "rehearse", "ballad")
        self.assertIsNone(result)
        self.assertIn("Visit the real stage", error)
        self.assertIsNone(self.tavern.db.village_stage)
        self.assertEqual(self.participation, [])

    def test_calling_change_cannot_sign_performance_work(self):
        self.before_commit = lambda: setattr(self.performer, "calling", "smith")
        result, error = self.act(self.performer, "rehearse", "reel")
        self.assertIsNone(result)
        self.assertIn("active Performer", error)
        self.assertIsNone(self.tavern.db.village_stage)
        self.assertEqual(self.participation, [])

    def test_identity_change_cannot_sign_old_account(self):
        self.before_commit = lambda: setattr(
            self.performer, "account",
            SimpleNamespace(id=99, sessions=SimpleNamespace(all=lambda: [object()])),
        )
        result, error = self.act(self.performer, "rehearse", "ballad")
        self.assertIsNone(result)
        self.assertIn("identity changed", error)
        self.assertIsNone(self.tavern.db.village_stage)

    def test_clock_change_does_not_sign_stage_event(self):
        self.before_commit = lambda: self.clock.__setitem__(1, 21)
        result, error = self.act(self.performer, "rehearse", "ballad")
        self.assertIsNone(result)
        self.assertIn("clock changed", error)
        self.assertIsNone(self.tavern.db.village_stage)

    def test_departed_witness_cannot_claim_firsthand_presence(self):
        state, ok, reason = stage_state.rehearse(
            None, day=1, hour=20, account_id=7, mask_id=70,
            mask="Musician", tune="ballad", event_id=20,
        )
        self.assertTrue(ok, reason)
        state, ok, reason = stage_state.perform(
            state, day=1, hour=20, account_id=7, mask_id=70,
            mask="Musician", tune="ballad", event_id=21,
            audience_account_ids=[8],
        )
        self.assertTrue(ok, reason)
        self.tavern.db.village_stage = state
        self.before_commit = lambda: setattr(self.listener, "location", None)
        result, error = self.act(self.listener, "witness")
        self.assertIsNone(result)
        self.assertIn("Visit the real stage", error)
        self.assertEqual(self.tavern.db.village_stage["witnesses"], [])
        self.assertEqual(self.participation, [])

    def test_valid_rehearsal_and_show_keep_real_audience(self):
        result, error = self.act(self.performer, "rehearse", "ballad")
        self.assertIsNone(error)
        self.assertEqual(result["action"], "rehearse")
        result, error = self.act(self.performer, "perform", "ballad")
        self.assertIsNone(error)
        self.assertEqual(result["action"], "perform")
        show = self.tavern.db.village_stage["performance"]
        self.assertEqual(show["account_id"], 7)
        self.assertEqual(show["eligible_audience_ids"], [8])
        self.assertEqual(len(self.participation), 2)


if __name__ == "__main__":
    unittest.main()
