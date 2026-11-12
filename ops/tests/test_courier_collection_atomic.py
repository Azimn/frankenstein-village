"""Execute the real courier collect body against adverse event interleavings."""
import ast
import contextlib
import sys
import types
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "spike/fvillage/world/courier_work.py"


class Box:
    def __init__(self, **values):
        self.__dict__.update(values)


class Db:
    def __init__(self, **values):
        self.__dict__.update(values)


class CourierCollectionAtomicity(unittest.TestCase):
    def test_collection_rechecks_clock_role_account_and_existing_parcel(self):
        source = ast.parse(SOURCE.read_text(encoding="utf-8"))
        fn = next(node for node in source.body if isinstance(node, ast.FunctionDef)
                  and node.name == "collect")
        script = compile(ast.Module(body=[fn], type_ignores=[]), str(SOURCE), "exec")
        for change in ("clock", "role", "account", "parcel", "location", "none"):
            with self.subTest(change=change):
                account = Box(id=11)
                mask = Box(id=101, account=account, contents=[])
                market = Box(id=7, db=Db(ferry_post_stock=None))
                mask.location = market
                now = [(4, 10)]
                role = ["wanderer"]
                created = []
                receipts = []
                class Atomic:
                    @staticmethod
                    @contextlib.contextmanager
                    def atomic():
                        yield
                def issue(state, day):
                    remaining = 2 if state is None else state["remaining"]
                    if remaining == 0:
                        return {"remaining": 0}, False
                    return {"remaining": remaining - 1}, True
                def create_object(*args, **kwargs):
                    created.append(kwargs)
                    return Box(id=88, db=Db(), **kwargs)
                def publish(kind, actor, payload, consequence):
                    if change == "clock":
                        now[0] = (5, 10)
                    elif change == "role":
                        role[0] = "merchant"
                    elif change == "account":
                        mask.account = Box(id=12)
                    elif change == "parcel":
                        mask.contents.append(Box(db=Db(ferry_parcel={"day": 4})))
                    elif change == "location":
                        mask.location = Box(id=8)
                    result = consequence({"id": 50})
                    receipts.append(result)
                    return {"id": 50}
                env = {
                    "_room": lambda name: market, "_access": lambda m, r: m.location is r,
                    "MARKET": "Market Lane", "PARCEL": "parcel",
                    "active_calling": lambda m: role[0],
                    "_clock": lambda: now[0],
                    "courier_state": Box(issue=issue),
                    "transaction": Atomic, "create_object": create_object,
                    "publish_world_event": publish,
                    "record_participation": lambda *a, **k: None,
                }
                exec(script, env)
                if change == "none":
                    result, error = env["collect"](mask)
                    self.assertIsNone(error)
                    self.assertEqual(len(created), 1)
                    self.assertEqual(market.db.ferry_post_stock["remaining"], 1)
                    self.assertEqual(result["event_id"], 50)
                else:
                    with self.assertRaises(RuntimeError):
                        env["collect"](mask)
                    self.assertEqual(created, [])
                    self.assertIsNone(market.db.ferry_post_stock)


if __name__ == "__main__":
    unittest.main()
