import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike" / "fvillage"))
from world.civic_commissions import refresh, pledge, finish, cancel, personal_agenda


def stage(state, day=1, supplier=101, bundle=450, event=10):
    return pledge(state, day, supplier, "Supplier", bundle_id=bundle, event_id=event)


def complete(state, day=1, finisher=202, bundle=450, event=11, space=True):
    return finish(state, day, finisher, "Finisher",
                  carried_bundle_id=bundle, reserve_has_space=space,
                  event_id=event)


class CivicCommissionTests(unittest.TestCase):
    def test_two_accounts_exact_same_physical_object_and_no_replay(self):
        state = refresh(None, 1)
        state, accepted, error = stage(state)
        self.assertTrue(accepted, error)
        self.assertEqual(state["commission"]["bundle_id"], 450)
        rejected, accepted, _ = stage(state, supplier=301, bundle=451)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)
        rejected, accepted, _ = complete(state, finisher=101)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)
        rejected, accepted, _ = complete(state, bundle=451)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)
        rejected, accepted, _ = complete(state, space=False)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)
        state, accepted, error = complete(state)
        self.assertTrue(accepted, error)
        self.assertEqual(state["commission"]["status"], "complete")
        self.assertEqual(state["commission"]["event_ids"], [10, 11])
        again, accepted, _ = complete(state, finisher=303, event=12)
        self.assertFalse(accepted)
        self.assertEqual(again, state)

    def test_bad_bundle_and_day_renewal(self):
        state = refresh(None, 1)
        rejected, accepted, _ = stage(state, bundle=-4)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)
        state, accepted, _ = stage(state)
        state = refresh(state, 2)
        self.assertEqual(state["history"][-1]["status"], "expired")
        self.assertEqual(state["commission"]["status"], "open")
        self.assertEqual(refresh(state, 1), state)
        rejected, accepted, _ = complete(state, 1)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)

    def test_restart_and_bounded_history(self):
        state = refresh(None, 4)
        state, _, _ = stage(state, day=4, supplier=10, bundle=99)
        restored = json.loads(json.dumps(state))
        restored, accepted, _ = complete(restored, day=4, finisher=11, bundle=99)
        self.assertTrue(accepted)
        for day in range(5, 50):
            restored = refresh(restored, day)
        self.assertLessEqual(len(restored["history"]), 32)
        self.assertEqual(restored["commission"]["id"], "civic-49")

    def test_many_days_restart_and_attempted_duplicate_claims(self):
        state = None
        for day in range(1, 251):
            state = refresh(state, day)
            expected_id = f"civic-{day}"
            state, accepted, _ = stage(
                state, day=day, supplier=100 + day, bundle=1000 + day,
                event=2 * day,
            )
            self.assertTrue(accepted)
            duplicate, accepted, _ = stage(
                state, day=day, supplier=9000, bundle=9000,
                event=9999,
            )
            self.assertFalse(accepted)
            self.assertEqual(duplicate, state)
            state = json.loads(json.dumps(state))
            state, accepted, _ = complete(
                state, day=day, finisher=500 + day,
                bundle=1000 + day, event=2 * day + 1,
            )
            self.assertTrue(accepted)
            self.assertEqual(state["commission"]["id"], expected_id)
            self.assertLessEqual(len(state["history"]), 32)
        self.assertEqual(state["history"][-1]["id"], "civic-250")

    def test_no_day_zero_or_backwards_refill(self):
        with self.assertRaises(ValueError):
            refresh(None, 0)
        state = refresh(None, 3)
        self.assertEqual(refresh(state, 2), state)
        stale, accepted, _ = stage(state, day=2)
        self.assertFalse(accepted)
        self.assertEqual(stale, state)
        stale, accepted, _ = complete(state, day=2)
        self.assertFalse(accepted)
        self.assertEqual(stale, state)


    def test_t13_supplier_cancels_before_neighbor_delivers(self):
        state, accepted, error = stage(refresh(None, 1))
        self.assertTrue(accepted, error)
        state, accepted, error = cancel(state, 1, 101, event_id=12)
        self.assertTrue(accepted, error)
        self.assertEqual(state["commission"]["status"], "cancelled")
        self.assertEqual(state["commission"]["bundle_id"], 450)
        self.assertEqual(state["commission"]["event_ids"], [10, 12])
        self.assertEqual(len(state["history"]), 1)
        self.assertEqual(state["history"][0]["status"], "cancelled")

        # A different account may still physically hold the bundle. Canceling
        # the ORDER cannot delete that object, mint a rack delivery or reopen it.
        replay, accepted, _ = complete(state, finisher=202, event=13)
        self.assertFalse(accepted)
        self.assertEqual(replay, state)
        replay, accepted, _ = cancel(state, 1, 101, event_id=14)
        self.assertFalse(accepted)
        self.assertEqual(replay, state)

        restored = json.loads(json.dumps(state))
        renewed = refresh(restored, 2)
        self.assertEqual(renewed["commission"]["status"], "open")
        self.assertEqual(len(renewed["history"]), 1)
        self.assertEqual(renewed["history"][0]["status"], "cancelled")
        self.assertEqual(renewed["history"][0]["bundle_id"], 450)

    def test_t13_neighbor_finishes_before_supplier_cancels(self):
        state, accepted, error = stage(refresh(None, 1))
        self.assertTrue(accepted, error)
        state, accepted, error = complete(state, finisher=202, event=11)
        self.assertTrue(accepted, error)
        self.assertEqual(state["commission"]["status"], "complete")
        self.assertEqual(len(state["history"]), 1)
        rejected, accepted, _ = cancel(state, 1, 101, event_id=12)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)
        rejected, accepted, _ = complete(state, finisher=303, event=13)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)
        self.assertEqual(len(state["history"]), 1)
        self.assertEqual(state["history"][0]["event_ids"], [10, 11])

    def test_t13_only_original_supplier_can_cancel_live_pledge(self):
        state = refresh(None, 1)
        rejected, accepted, _ = cancel(state, 1, 101, event_id=12)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)
        state, accepted, error = stage(state)
        self.assertTrue(accepted, error)
        with self.assertRaises(ValueError):
            cancel(state, 0, 101, event_id=12)
        for account, day, event in (
            (202, 1, 12), (101, 1, 0), (101, 1, -2)
        ):
            rejected, accepted, _ = cancel(state, day, account, event_id=event)
            self.assertFalse(accepted)
            self.assertEqual(rejected, state)
        rejected, accepted, _ = cancel(state, 1, 101, event_id=True)
        self.assertFalse(accepted)
        self.assertEqual(rejected, state)


    def test_t13_mixed_cancelled_and_completed_orders_remain_bounded(self):
        """Repeated day changes preserve one terminal record per order.

        Cancellation cannot add an expiry record on the following day,
        including after JSON roundtrips and repeated board refreshes.
        """
        state = None
        for day in range(1, 81):
            state = refresh(state, day)
            supplier = 100 + day
            bundle = 1000 + day
            state, accepted, error = stage(
                state, day=day, supplier=supplier, bundle=bundle,
                event=day * 10,
            )
            self.assertTrue(accepted, error)
            if day % 2:
                state, accepted, error = cancel(
                    state, day, supplier, event_id=day * 10 + 1,
                )
                expected = "cancelled"
            else:
                state, accepted, error = complete(
                    state, day=day, finisher=500 + day,
                    bundle=bundle, event=day * 10 + 1,
                )
                expected = "complete"
            self.assertTrue(accepted, error)
            self.assertEqual(state["commission"]["status"], expected)
            self.assertEqual(state["commission"]["event_ids"],
                             [day * 10, day * 10 + 1])

            # Simulate serialization between sessions; repeat status reads
            # and rejected terminal actions without changing persisted data.
            state = json.loads(json.dumps(state))
            for _ in range(3):
                self.assertEqual(refresh(state, day), state)
                replay, accepted, _ = cancel(
                    state, day, supplier, event_id=day * 10 + 2,
                )
                self.assertFalse(accepted)
                self.assertEqual(replay, state)

            state = refresh(state, day + 1)
            self.assertEqual(state["commission"]["status"], "open")
            self.assertEqual(len(state["history"]), min(day, 32))
            self.assertEqual(state["history"][-1]["id"], f"civic-{day}")
            self.assertEqual(state["history"][-1]["status"], expected)
            self.assertEqual(state["history"][-1]["bundle_id"], bundle)
            self.assertEqual(refresh(state, day + 1), state)

        self.assertEqual(
            [item["id"] for item in state["history"]],
            [f"civic-{day}" for day in range(49, 81)],
        )


    def test_t13_all_serialized_terminal_action_interleavings(self):
        """All 720 six-action schedules produce one terminal result, never two.

        The Evennia command loop serializes actual command consequences.
        This checks the pure state transition against every ordering of
        two legitimate cancellations, two legitimate deliveries, and two
        unauthorized/invalid attempts. It is NOT a simultaneous socket race.
        """
        from itertools import permutations

        actions = ("cancel_a", "finish_a", "cancel_b", "finish_b",
                   "wrong_account", "wrong_bundle")
        winners = {"cancel_a", "cancel_b", "finish_a", "finish_b"}
        event_ids = {action: 20 + index for index, action in enumerate(actions)}
        for schedule in permutations(actions):
            with self.subTest(schedule=schedule):
                state, accepted, error = stage(refresh(None, 1))
                self.assertTrue(accepted, error)
                successful = []
                for action in schedule:
                    previous = json.loads(json.dumps(state))
                    if action in ("cancel_a", "cancel_b"):
                        state, accepted, _ = cancel(
                            state, 1, 101, event_id=event_ids[action],
                        )
                    elif action == "wrong_account":
                        state, accepted, _ = cancel(
                            state, 1, 303, event_id=event_ids[action],
                        )
                    else:
                        state, accepted, _ = complete(
                            state, finisher=202,
                            bundle=450 if action != "wrong_bundle" else 999,
                            event=event_ids[action],
                        )
                    if accepted:
                        successful.append(action)
                    else:
                        self.assertEqual(state, previous)
                    state = json.loads(json.dumps(state))

                first_valid = next(action for action in schedule if action in winners)
                self.assertEqual(successful, [first_valid])
                expected_status = (
                    "cancelled" if first_valid.startswith("cancel") else "complete"
                )
                self.assertEqual(state["commission"]["status"], expected_status)
                self.assertEqual(
                    state["commission"]["event_ids"], [10, event_ids[first_valid]]
                )
                self.assertEqual(len(state["history"]), 1)
                self.assertEqual(state["history"][0], state["commission"])
                renewed = refresh(state, 2)
                self.assertEqual(len(renewed["history"]), 1)
                self.assertEqual(renewed["history"][0]["status"], expected_status)
                self.assertEqual(renewed["commission"]["status"], "open")


    def test_t13_signed_state_rejects_invalid_actor_item_and_receipt_ids(self):
        """Invalid receipts and actors must never become signed order history.

        The ordinary command service supplies real positive integer event IDs.
        A pure-state boundary must not silently coerce booleans, strings or
        zero into apparent canonical ledger references.
        """
        base = refresh(None, 1)
        for invalid in (None, True, False, 0, -1, "17", 3.5):
            with self.subTest(stage_receipt=invalid):
                result, accepted, _ = pledge(
                    base, 1, 101, "Supplier", bundle_id=450,
                    event_id=invalid,
                )
                self.assertFalse(accepted)
                self.assertEqual(result, base)

            with self.subTest(stage_actor=invalid):
                result, accepted, _ = pledge(
                    base, 1, invalid, "Supplier", bundle_id=450,
                    event_id=10,
                )
                self.assertFalse(accepted)
                self.assertEqual(result, base)

        for invalid_bundle in (None, True, False, 0, -1, "450", 4.5):
            with self.subTest(stage_bundle=invalid_bundle):
                result, accepted, _ = pledge(
                    base, 1, 101, "Supplier", bundle_id=invalid_bundle,
                    event_id=10,
                )
                self.assertFalse(accepted)
                self.assertEqual(result, base)

        pledged, accepted, error = stage(base)
        self.assertTrue(accepted, error)
        for invalid in (None, True, False, 0, -1, "18", 3.5):
            with self.subTest(finish_receipt=invalid):
                result, accepted, _ = finish(
                    pledged, 1, 202, "Finisher",
                    carried_bundle_id=450, reserve_has_space=True,
                    event_id=invalid,
                )
                self.assertFalse(accepted)
                self.assertEqual(result, pledged)

            with self.subTest(finish_actor=invalid):
                result, accepted, _ = finish(
                    pledged, 1, invalid, "Finisher",
                    carried_bundle_id=450, reserve_has_space=True,
                    event_id=11,
                )
                self.assertFalse(accepted)
                self.assertEqual(result, pledged)

        # Python bool is a subclass of int; it is not a physical object ID.
        one, accepted, error = pledge(
            base, 1, 101, "Supplier", bundle_id=1, event_id=10,
        )
        self.assertTrue(accepted, error)
        rejected, accepted, _ = finish(
            one, 1, 202, "Finisher",
            carried_bundle_id=True, reserve_has_space=True, event_id=11,
        )
        self.assertFalse(accepted)
        self.assertEqual(rejected, one)



    def test_t13_terminal_event_must_not_reuse_pledge_receipt(self):
        """A terminal action cannot cite its own pledge as a second signed event.

        This pure boundary must reject duplicate provenance even when the
        normal Evennia ledger supplies unique IDs. Rejection cannot mutate
        the live order or add a terminal history entry.
        """
        pledged, accepted, error = stage(refresh(None, 1), event=10)
        self.assertTrue(accepted, error)
        original = json.loads(json.dumps(pledged))
        for action in ("finish", "cancel"):
            with self.subTest(action=action):
                if action == "finish":
                    result, accepted, _ = complete(
                        pledged, day=1, finisher=202, bundle=450, event=10,
                    )
                else:
                    result, accepted, _ = cancel(
                        pledged, 1, 101, event_id=10,
                    )
                self.assertFalse(accepted)
                self.assertEqual(result, original)
                self.assertEqual(pledged, original)
                self.assertEqual(pledged["history"], [])

        completed, accepted, error = complete(
            pledged, day=1, finisher=202, bundle=450, event=11,
        )
        self.assertTrue(accepted, error)
        self.assertEqual(completed["commission"]["event_ids"], [10, 11])
        self.assertEqual(len(completed["history"]), 1)


    def test_t16_returning_player_sees_real_commission_outcome(self):
        """No phantom delivery, and the original supplier sees a true outcome."""
        state, ok, reason = stage(refresh(None, 1))
        self.assertTrue(ok, reason)
        pending = " ".join(personal_agenda(state, 1, 101, [450]))
        self.assertIn("pending", pending)
        self.assertIn("commission cancel", pending)
        self.assertEqual(personal_agenda(state, 1, 303, []), [])
        carrier = " ".join(personal_agenda(state, 1, 202, [450]))
        self.assertIn("commission deliver", carrier)
        self.assertEqual(personal_agenda(state, 1, 202, [999]), [])

        completed, ok, reason = complete(state)
        self.assertTrue(ok, reason)
        completed = json.loads(json.dumps(completed))
        self.assertIn("completed by another account",
                      " ".join(personal_agenda(completed, 1, 101)))
        self.assertIn("your delivery is complete",
                      " ".join(personal_agenda(completed, 1, 202)))
        self.assertEqual(personal_agenda(completed, 1, 303), [])

        cancelled, ok, reason = cancel(state, 1, 101, event_id=12)
        self.assertTrue(ok, reason)
        self.assertIn("cancelled",
                      " ".join(personal_agenda(cancelled, 1, 101)))
        self.assertEqual(personal_agenda(cancelled, 1, 202, [450]), [])

        expired = refresh(json.loads(json.dumps(state)), 2)
        self.assertIn("yesterday's pledge expired",
                      " ".join(personal_agenda(expired, 2, 101)))
        self.assertNotIn("pending",
                         " ".join(personal_agenda(expired, 2, 101)))
        self.assertEqual(personal_agenda(expired, 2, 202, [450]), [])
        self.assertEqual(personal_agenda(state, 1, True, [450]), [])
        self.assertEqual(personal_agenda(state, 1, 202, [True]), [])



    def test_t13_village_day_requires_an_exact_positive_integer(self):
        """No truncated or coerced clock values may sign a daily commission.

        World clock days are integers. Accepting True as day one, or
        truncating 2.9 to day two, can attach a real signed event to the
        wrong daily order. Rejected inputs must leave prior state untouched.
        """
        baseline = refresh(None, 2)
        pledged, accepted, error = stage(
            baseline, day=2, supplier=101, bundle=450, event=10,
        )
        self.assertTrue(accepted, error)
        original = json.loads(json.dumps(pledged))
        for bad_day in (
            None, True, False, 0, -1, 2.9, 0.9, "2", "2.9",
            float("nan"), float("inf"),
        ):
            with self.subTest(day=repr(bad_day)):
                with self.assertRaises(ValueError):
                    refresh(pledged, bad_day)
                with self.assertRaises(ValueError):
                    pledge(
                        pledged, bad_day, 101, "Supplier",
                        bundle_id=451, event_id=20,
                    )
                with self.assertRaises(ValueError):
                    finish(
                        pledged, bad_day, 202, "Finisher",
                        carried_bundle_id=450, reserve_has_space=True,
                        event_id=21,
                    )
                with self.assertRaises(ValueError):
                    cancel(pledged, bad_day, 101, event_id=22)
                self.assertEqual(pledged, original)
        self.assertEqual(refresh(pledged, 2), original)


if __name__ == "__main__":
    unittest.main()
