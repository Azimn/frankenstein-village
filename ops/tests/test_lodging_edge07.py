"""GDD-EDGE-07: real Innkeep disclosure and separate Detective register inquiry."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))
from world import lodging_state as rules


def worker(account=11, mask_id=111, name="InnkeepTester", event=100,
           day=1, hour=18):
    return {
        "day": day, "hour": hour, "account_id": account,
        "mask_id": mask_id, "mask": name, "event_id": event,
        "register_id": 401, "room_id": 301,
    }


def inquiry(event=200, day=1, hour=19, account=22, mask_id=222,
            source=100):
    return {
        **worker(account=account, mask_id=mask_id, name="DetectiveTester",
                 event=event, day=day, hour=hour),
        "source_event_id": source,
    }


def signed_source(row):
    return {
        "id": row["event_id"],
        "kind": "village.lodging_disclosure",
        "status": "complete",
        "actor": {
            "account_id": row["account_id"], "mask_id": row["mask_id"],
            "mask": row["mask"],
        },
        "payload": {
            "calling": "innkeep", "scope": rules.SCOPE,
            "day": row["day"], "hour": row["hour"],
            "register_id": row["register_id"], "room_id": row["room_id"],
        },
        "consequence": {
            "scope": rules.SCOPE, "register_id": row["register_id"],
            "room_id": row["room_id"], "source_event_id": row["event_id"],
            "day": row["day"], "hour": row["hour"],
        },
    }


def signed_inquiry(row):
    record = row["inquiry"]
    return {
        "id": record["event_id"],
        "kind": "village.lodging_inquiry",
        "status": "complete",
        "actor": {
            "account_id": record["account_id"],
            "mask_id": record["mask_id"],
            "mask": record["mask"],
        },
        "payload": {
            "calling": "detective", "scope": rules.SCOPE,
            "day": record["day"], "hour": record["hour"],
            "register_id": row["register_id"], "room_id": row["room_id"],
            "source_event_id": row["event_id"],
        },
        "consequence": {
            "scope": rules.SCOPE,
            "day": record["day"], "hour": record["hour"],
            "register_id": row["register_id"], "room_id": row["room_id"],
            "source_event_id": row["event_id"],
            "finding": "qualified_register_observation",
        },
    }


class LodgingEdge07Tests(unittest.TestCase):
    def setUp(self):
        self.state, okay, error = rules.disclose(None, **worker())
        self.assertTrue(okay, error)

    def test_two_distinct_professional_actions_persist(self):
        self.assertTrue(rules.source_is_valid(
            signed_source(self.state["records"][0]), self.state["records"][0]))
        after, okay, error = rules.inquire(self.state, **inquiry())
        self.assertTrue(okay, error)
        self.assertEqual(after["records"][0]["inquiry"]["source_event_id"], 100)
        self.assertEqual(after["records"][0]["inquiry"]["account_id"], 22)
        self.assertEqual(after["records"][0]["inquiry"]["finding"],
                         "qualified_register_observation")
        self.assertNotIn("culprit", rules.public_lines(after).lower())
        self.assertIn("no guest identity", rules.public_lines(after).lower())

    def test_public_readback_requires_both_completed_canonical_events(self):
        state, okay, error = rules.inquire(self.state, **inquiry())
        self.assertTrue(okay, error)
        row = state["records"][0]
        events = {
            100: signed_source(row),
            200: signed_inquiry(row),
        }
        self.assertTrue(rules.inquiry_is_valid(events[200], row))
        rendered = rules.public_lines(
            json.loads(json.dumps(state)), event_lookup=events.get,
            register_id=401, room_id=301,
        )
        self.assertIn("Latest redacted authorization", rendered)
        self.assertIn("Independent qualified inquiry: signed event 200", rendered)
        self.assertNotIn("DetectiveTester", rendered)
        self.assertNotIn("InnkeepTester", rendered)
        self.assertIn("No guest identity is established", rendered)

        missing_inquiry = rules.public_lines(
            state, event_lookup={100: events[100]}.get,
            register_id=401, room_id=301,
        )
        self.assertIn("Stored Detective inquiry cannot be verified", missing_inquiry)
        self.assertNotIn("Independent qualified inquiry: signed", missing_inquiry)
        missing_source = rules.public_lines(
            state, event_lookup={200: events[200]}.get,
            register_id=401, room_id=301,
        )
        self.assertIn("no signed disclosure or inquiry is shown", missing_source)
        self.assertNotIn("Latest redacted authorization:", missing_source)

    def test_public_readback_fails_closed_without_ledger_or_physical_register(self):
        row = self.state["records"][0]
        source = signed_source(row)
        for lookup, register_id, room_id in (
            (None, 401, 301),
            ({100: source}.get, 999, 301),
            ({100: source}.get, 401, 999),
            (lambda _id: (_ for _ in ()).throw(RuntimeError("ledger unavailable")), 401, 301),
        ):
            output = rules.public_lines(
                self.state, event_lookup=lookup,
                register_id=register_id, room_id=room_id,
            )
            self.assertIn("cannot be verified", output)
            self.assertNotIn("Latest redacted authorization:", output)
        valid = rules.public_lines(
            self.state, event_lookup={100: source}.get,
            register_id=401, room_id=301,
        )
        self.assertIn("Latest redacted authorization", valid)
        self.assertIn("No independent Detective inquiry", valid)

    def test_forged_inquiry_never_becomes_public_signed_evidence(self):
        state, okay, error = rules.inquire(self.state, **inquiry())
        self.assertTrue(okay, error)
        row = state["records"][0]
        source, original = signed_source(row), signed_inquiry(row)
        for group, field, bad in (
            (None, "id", 999),
            (None, "kind", "village.lodging_disclosure"),
            (None, "status", "consequence_failed"),
            ("actor", "account_id", 11),
            ("actor", "mask_id", 999),
            ("payload", "calling", "innkeep"),
            ("payload", "register_id", 999),
            ("payload", "room_id", 999),
            ("payload", "source_event_id", 999),
            ("payload", "hour", 23),
            ("consequence", "finding", "guest_identified"),
            ("consequence", "source_event_id", 999),
            ("consequence", "day", 9),
            ("consequence", "scope", "full_guest_record"),
        ):
            forged = copy.deepcopy(original)
            if group is None:
                forged[field] = bad
            else:
                forged[group][field] = bad
            self.assertFalse(rules.inquiry_is_valid(forged, row), (group, field))
            output = rules.public_lines(
                state, event_lookup={100: source, 200: forged}.get,
                register_id=401, room_id=301,
            )
            self.assertIn("Stored Detective inquiry cannot be verified", output)
            self.assertNotIn("Independent qualified inquiry: signed", output)

        corrupted = json.loads(json.dumps(state))
        corrupted["records"][0]["inquiry"]["account_id"] = 77
        output = rules.public_lines(
            corrupted, event_lookup={100: source, 200: original}.get,
            register_id=401, room_id=301,
        )
        self.assertIn("cannot be verified", output)
        self.assertNotIn("Independent qualified inquiry: signed", output)

    def test_one_disclosure_per_day_is_finite(self):
        before = copy.deepcopy(self.state)
        after, okay, error = rules.disclose(
            self.state, **worker(account=33, mask_id=333, event=101, hour=19))
        self.assertFalse(okay)
        self.assertIn("already authorized", error)
        self.assertEqual(after, before)

    def test_same_account_switching_roles_is_rejected(self):
        after, okay, error = rules.inquire(
            self.state, **inquiry(account=11, mask_id=333))
        self.assertFalse(okay)
        self.assertIn("same account", error)
        self.assertIsNone(after["records"][0]["inquiry"])

    def test_forged_source_event_and_wrong_role_fail_closed(self):
        row = self.state["records"][0]
        original = signed_source(row)
        for field, bad in [
            ("id", 999), ("kind", "village.lodging_inquiry"),
            ("status", "consequence_failed"),
        ]:
            forged = copy.deepcopy(original)
            forged[field] = bad
            self.assertFalse(rules.source_is_valid(forged, row), field)
        for group, field, bad in [
            ("actor", "account_id", 22),
            ("actor", "mask_id", 999),
            ("actor", "mask", "Forged"),
            ("payload", "calling", "detective"),
            ("payload", "room_id", 999),
            ("payload", "register_id", 999),
            ("payload", "hour", 22),
            ("payload", "scope", "full_guest_record"),
            ("consequence", "source_event_id", 999),
            ("consequence", "scope", "private_guest_details"),
        ]:
            forged = copy.deepcopy(original)
            forged[group][field] = bad
            self.assertFalse(rules.source_is_valid(forged, row), (group, field))
        self.assertFalse(rules.source_is_valid(None, row))
        self.assertFalse(rules.source_is_valid(original, None))

    def test_missing_or_wrong_physical_register_rejected(self):
        after, okay, error = rules.inquire(
            self.state, **inquiry(source=999))
        self.assertFalse(okay)
        self.assertIn("No signed", error)
        args = inquiry()
        args["register_id"] = 999
        after, okay, error = rules.inquire(self.state, **args)
        self.assertFalse(okay)
        self.assertIn("another physical register", error)

    def test_duplicate_detective_inquiry_does_not_create_history(self):
        after, okay, error = rules.inquire(self.state, **inquiry())
        self.assertTrue(okay, error)
        unchanged, okay, error = rules.inquire(
            after, **inquiry(event=201, account=44, mask_id=444, hour=20))
        self.assertFalse(okay)
        self.assertIn("already has", error)
        self.assertEqual(unchanged, after)

    def test_clock_rewind_future_and_stale_source(self):
        after, okay, error = rules.inquire(
            self.state, **inquiry(hour=17))
        self.assertFalse(okay)
        self.assertIn("rewound", error)
        after, okay, error = rules.inquire(
            self.state, **inquiry(day=4, hour=0))
        self.assertFalse(okay)
        self.assertIn("stale", error)
        self.assertIsNone(after["records"][0]["inquiry"])

    def test_later_day_inquiry_within_48_hours(self):
        after, okay, error = rules.inquire(
            self.state, **inquiry(day=3, hour=17))
        self.assertTrue(okay, error)
        self.assertEqual(after["records"][0]["inquiry"]["day"], 3)
        future, okay, error = rules.disclose(
            after, **worker(day=2, event=101))
        self.assertFalse(okay)
        self.assertIn("rewound", error)
        new, okay, error = rules.disclose(
            after, **worker(day=4, hour=18, event=102))
        self.assertTrue(okay, error)
        self.assertEqual(len(new["records"]), 2)

    def test_json_restart_round_trip_preserves_original_authority(self):
        after, okay, error = rules.inquire(self.state, **inquiry())
        self.assertTrue(okay, error)
        restored = rules.normalize(json.loads(json.dumps(after)))
        self.assertEqual(restored, after)
        self.assertTrue(rules.source_is_valid(
            signed_source(restored["records"][0]), restored["records"][0]))
        self.assertEqual(restored["last_day"], 1)
        self.assertEqual(restored["last_hour"], 19)

    def test_invalid_identity_time_and_malformed_history_fail_closed(self):
        for key, value in [
            ("account_id", True), ("mask_id", 0),
            ("event_id", "bad"), ("register_id", -1),
            ("room_id", None), ("hour", 24), ("day", False),
        ]:
            args = worker(event=101, day=2)
            args[key] = value
            _state, okay, _error = rules.disclose(self.state, **args)
            self.assertFalse(okay, key)
        broken = {"records": [
            {"day": 1, "hour": 18, "account_id": True},
            self.state["records"][0],
            {**self.state["records"][0], "event_id": 999},
        ]}
        restored = rules.normalize(broken)
        self.assertEqual(len(restored["records"]), 1)
        self.assertIsNone(restored["records"][0]["inquiry"])


if __name__ == "__main__":
    unittest.main()
