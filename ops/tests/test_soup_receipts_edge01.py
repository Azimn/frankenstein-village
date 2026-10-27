"""EDGE-01: actual finite kitchen source, consent, independent publication."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import soup_receipts, soup_state


INN = {"account_id": 11, "mask_id": 101, "mask": "InnkeepTester"}
CHRON = {"account_id": 12, "mask_id": 102, "mask": "SmokeTester"}
OTHER_MASK_SAME_ACCOUNT = {
    "account_id": 11, "mask_id": 103, "mask": "OtherMask"
}


def fixture():
    recipe = soup_state.produce("turnip", "thyme", warmed=False)
    state = soup_state.archive(
        None, 1, maker_id=101, maker="InnkeepTester",
        source_event_id=30, cook_event_id=31, recipe=recipe,
    )
    prep = {
        "id": 30, "kind": "professional.innkeep_soup_prepared",
        "status": "complete", "actor": INN,
        "payload": {"day": 1, "base": "turnip", "seasoning": "thyme",
                    "room_id": 55},
        "consequence": {"packet_id": 901},
    }
    cooked = {
        "id": 31, "kind": "professional.innkeep_soup_cooked",
        "status": "complete", "actor": INN,
        "payload": {
            "day": 1, "base": "turnip", "seasoning": "thyme",
            "prep_event_id": 30, "packet_id": 901,
        },
        "consequence": {
            "bowl_id": 902, "quality": recipe["quality"],
            "pantry_room_id": 55,
            "source_event_id": 30,
        },
    }
    return state, cooked, prep


def disclosure():
    return {
        "id": 32,
        "kind": "professional.innkeep_house_receipt_disclosed",
        "status": "complete",
        "actor": copy.deepcopy(INN),
        "payload": {
            "cook_event_id": 31, "day": 1, "hour": 12,
            "scope": "public_kitchen_batch_only",
        },
        "consequence": {
            "cook_event_id": 31, "scope": "public_kitchen_batch_only",
        },
    }


def consent(state, cooked, prep, **changes):
    args = {
        "batch_id": 31, "actor": INN, "day": 1, "hour": 12,
        "event_id": 32, "cooked": cooked, "prepared": prep,
    }
    args.update(changes)
    return soup_receipts.authorize(state, **args)


def publish(state, cooked, prep, **changes):
    args = {
        "batch_id": 31, "actor": CHRON, "day": 1, "hour": 13,
        "event_id": 33, "cooked": cooked, "prepared": prep,
        "consent_event": disclosure(),
    }
    args.update(changes)
    return soup_receipts.publish(state, **args)


class HouseReceiptTests(unittest.TestCase):
    def test_independent_accounts_publish_only_consented_house_facts(self):
        state, cooked, prep = fixture()
        authorized, record, error = consent(state, cooked, prep)
        self.assertIsNone(error)
        self.assertEqual(record["account_id"], 11)
        self.assertNotIn("consent", state["history"][0])
        published, record, error = publish(authorized, cooked, prep)
        self.assertIsNone(error)
        self.assertEqual(record["account_id"], 12)
        self.assertEqual(record["consent_event_id"], 32)
        self.assertEqual(record["cook_event_id"], 31)
        lines = soup_receipts.public_lines(published, 1)
        self.assertIn("event 31", lines)
        self.assertIn("consent event 32", lines)
        self.assertIn("publication event 33", lines)
        self.assertIn("not a guest list", lines)
        self.assertNotIn("guest identity", lines)

    def test_no_consent_no_publication(self):
        state, cooked, prep = fixture()
        unchanged, result, error = publish(state, cooked, prep)
        self.assertIsNone(result)
        self.assertIn("not authorized", error)
        self.assertEqual(unchanged, state)

    def test_same_account_new_mask_cannot_play_both_roles(self):
        state, cooked, prep = fixture()
        state, _, _ = consent(state, cooked, prep)
        unchanged, result, error = publish(
            state, cooked, prep, actor=OTHER_MASK_SAME_ACCOUNT
        )
        self.assertIsNone(result)
        self.assertIn("independent Chronicler account", error)
        self.assertEqual(unchanged, state)

    def test_cooking_authorization_requires_original_signed_innkeep(self):
        state, cooked, prep = fixture()
        for actor in (CHRON, OTHER_MASK_SAME_ACCOUNT, {
            "account_id": True, "mask_id": 101, "mask": "InnkeepTester",
        }):
            unchanged, result, error = consent(
                state, cooked, prep, actor=actor
            )
            self.assertIsNone(result)
            self.assertIn("matching signed Innkeep", error)
            self.assertEqual(unchanged, state)

    def test_failed_or_forged_cooking_and_prep_cannot_authorize(self):
        state, cooked, prep = fixture()
        variants = [
            ({"status": "consequence_failed"}, {}),
            ({"actor": {"account_id": 99, "mask_id": 101,
                        "mask": "InnkeepTester"}}, {}),
            ({"consequence": {"quality": 34, "bowl_id": 902,
                              "source_event_id": 999}}, {}),
            ({"payload": {"day": 1, "base": "barley",
                          "seasoning": "thyme", "prep_event_id": 30}}, {}),
            ({}, {"status": "consequence_failed"}),
            ({}, {"consequence": {"packet_id": 0}}),
            ({}, {"actor": {"account_id": None, "mask_id": 101,
                            "mask": "InnkeepTester"}}),
            ({"payload": {"day": 1, "base": "turnip",
                          "seasoning": "thyme", "prep_event_id": 30,
                          "packet_id": 999}}, {}),
            ({}, {"payload": {"day": 1, "base": "turnip",
                              "seasoning": "thyme", "room_id": 999}}),
        ]
        for cook_patch, prep_patch in variants:
            c = {**cooked, **cook_patch}
            p = {**prep, **prep_patch}
            _, result, error = consent(state, c, p)
            self.assertIsNone(result)
            self.assertIn("matching signed Innkeep", error)

    def test_forged_failed_or_mismatched_disclosure_cannot_publish(self):
        state, cooked, prep = fixture()
        state, _, _ = consent(state, cooked, prep)
        variants = [
            {"status": "consequence_failed"},
            {"actor": CHRON},
            {"payload": {"cook_event_id": 999, "day": 1, "hour": 12,
                         "scope": "public_kitchen_batch_only"}},
            {"consequence": {"cook_event_id": 31, "scope": "private_guest_data"}},
            {"kind": "village.fake_disclosure"},
        ]
        for patch in variants:
            forged = {**disclosure(), **patch}
            unchanged, result, error = publish(
                state, cooked, prep, consent_event=forged
            )
            self.assertIsNone(result)
            self.assertIsNotNone(error)
            self.assertEqual(unchanged, state)

    def test_duplicate_consent_and_publication_rejected(self):
        state, cooked, prep = fixture()
        state, _, _ = consent(state, cooked, prep)
        unchanged, result, error = consent(
            state, cooked, prep, event_id=35
        )
        self.assertIsNone(result)
        self.assertIn("already", error)
        self.assertEqual(unchanged, state)
        state, _, _ = publish(state, cooked, prep)
        unchanged, result, error = publish(
            state, cooked, prep, event_id=36
        )
        self.assertIsNone(result)
        self.assertIn("already published", error)
        self.assertEqual(unchanged, state)

    def test_invalid_time_and_late_publication(self):
        state, cooked, prep = fixture()
        _, result, error = consent(
            state, cooked, prep, day=4
        )
        self.assertIsNone(result)
        self.assertIn("outside", error)
        state, _, _ = consent(state, cooked, prep)
        for day, hour in ((1, 11), (4, 13), (0, 12), (1, 24)):
            _, result, error = publish(
                state, cooked, prep, day=day, hour=hour
            )
            self.assertIsNone(result)
            self.assertIsNotNone(error)

    def test_json_restart_and_next_day_preserve_signed_history(self):
        state, cooked, prep = fixture()
        state, _, _ = consent(state, cooked, prep)
        state, _, _ = publish(state, cooked, prep)
        restored = json.loads(json.dumps(state))
        nextday = soup_state.pantry(restored, 2)
        self.assertEqual(nextday["stock"], soup_state.BASE_STOCK)
        self.assertEqual(nextday["history"][0]["publication"]["event_id"], 33)
        self.assertIn("Chronicler SmokeTester", soup_receipts.public_lines(
            nextday, 2
        ))
        self.assertEqual(
            soup_state.pantry(restored, 1)["history"][0]["consent"]["event_id"],
            32,
        )

    def test_wrong_batch_and_event_order_do_not_create_receipts(self):
        state, cooked, prep = fixture()
        for batch_id, event_id in ((999, 1000), (31, 31), (31, 0)):
            _, result, error = consent(
                state, cooked, prep, batch_id=batch_id, event_id=event_id
            )
            self.assertIsNone(result)
            self.assertIsNotNone(error)


if __name__ == "__main__":
    unittest.main()
