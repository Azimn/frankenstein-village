"""EDGE-08 pure provenance, scarcity, negative and restart-survival tests."""
import copy
import json
from collections import UserDict, UserList
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "spike/fvillage"))

from world import refuge_state as r, soup_state
from world.discoveries import observed_caution


def fixture():
    protection = {
        "id": 41, "kind": "village.route_protected", "status": "complete",
        "actor": {"account_id": 101, "mask_id": 201, "mask": "HoundTester"},
        "payload": {"site": "red_cord", "role": "hound", "action": "protect",
                    "location": r.TREELINE, "day": 3, "hour": 10},
        "consequence": {"cord_object_id": 301, "day": 3,
                        "caution_marked": True},
    }
    marker = {"event_id": 41, "account_id": 101,
              "mask": "HoundTester", "day": 3}
    dispatch = {
        "id": 42, "kind": "professional.hound_refuge_dispatch",
        "status": "complete",
        "actor": {"account_id": 101, "mask_id": 201, "mask": "HoundTester"},
        "payload": {"day": 3, "hour": 11, "cord_id": 301,
                    "source_protect_event_id": 41,
                    "professional_calling": "hound",
                    "location": r.TREELINE},
        "consequence": {"item_id": 401, "cord_id": 301,
                        "source_protect_event_id": 41},
    }
    token = {"dispatch_event_id": 42, "source_protect_event_id": 41,
             "hound_account_id": 101, "hound_mask_id": 201,
             "cord_id": 301, "day": 3, "hour": 11}
    return protection, marker, dispatch, token


def serve(**changes):
    source, marker, event, token = fixture()
    args = dict(raw=None, pantry_raw=None, day=3, hour=12,
                innkeep_account_id=102, innkeep_mask_id=202,
                hound_account_id=101, hound_mask_id=201,
                token=token, token_id=401, dispatch_event=event,
                protection=source, marker=marker, cord_id=301,
                tavern_id=501, event_id=43)
    args.update(changes)
    return r.accept(**args)


class RefugeRules(unittest.TestCase):
    def test_real_two_account_arrival_spends_finite_food(self):
        history, food, ok, reason = serve()
        self.assertTrue(ok, reason)
        self.assertEqual(food["stock"]["turnip"], 2)
        self.assertEqual(food["stock"]["salt"], 3)
        self.assertEqual(history["history"][0]["dispatch_event_id"], 42)
        self.assertEqual(history["history"][0]["hound_account_id"], 101)
        self.assertEqual(history["history"][0]["innkeep_account_id"], 102)

    def test_fractional_signed_ids_and_clock_never_spend_refuge_food(self):
        # int(41.9) == 41 is not proof of a signed event, player or item.
        self.assertEqual(r.ident(41), 41)
        self.assertEqual(r.ident("41"), 41)
        self.assertIsNone(r.ident(41.9))
        self.assertIsNone(r.ident("41.9"))
        self.assertIsNone(r.ident(True))
        self.assertEqual(r.stamp("3", "11"), r.stamp(3, 11))
        for day, hour in ((3.9, 11), (3, 11.9), (3, True),
                          ("3.9", 11), (3, "11.9")):
            self.assertIsNone(r.stamp(day, hour))

        source, marker, dispatch, token = fixture()
        bad_cases = (
            {"token": dict(token, dispatch_event_id=42.9)},
            {"token": dict(token, source_protect_event_id=41.9)},
            {"token": dict(token, cord_id=301.9)},
            {"token": dict(token, hound_account_id=101.9)},
            {"token": dict(token, hound_mask_id=201.9)},
            {"dispatch_event": dict(dispatch, id=42.9)},
            {"protection": dict(source, id=41.9)},
            {"marker": dict(marker, event_id=41.9)},
            {"marker": dict(marker, account_id=101.9)},
            {"dispatch_event": dict(
                dispatch, payload=dict(dispatch["payload"], hour=11.9))},
            {"token": dict(token, hour=11.9)},
            {"token": dict(token, day=3.9)},
            {"day": 3.9},
            {"hour": 12.9},
        )
        for changes in bad_cases:
            with self.subTest(changes=changes):
                state, food, allowed, _reason = serve(**changes)
                self.assertFalse(allowed)
                self.assertIsNone(state)
                pantry_day = max(1, r.ident(changes.get("day", 3)) or 1)
                self.assertEqual(food, soup_state.pantry(None, pantry_day))

    def test_missing_paired_signed_protection_fields_cannot_spend_food(self):
        # Two absent values must not authenticate each other merely because
        # ident(None) == ident(None). This is corrupted-source integrity, not
        # a claim that an ordinary player can edit the canonical event ledger.
        source, marker, _dispatch, _token = fixture()
        cases = (
            ("event ID absent", "id", "event_id", None),
            ("event ID boolean", "id", "event_id", True),
            ("actor account absent", "account_id", "account_id", None),
            ("actor account boolean", "account_id", "account_id", True),
            ("actor mask name absent", "mask", "mask", None),
        )
        for label, event_key, marker_key, value in cases:
            with self.subTest(case=label):
                bad_source = copy.deepcopy(source)
                bad_marker = copy.deepcopy(marker)
                if event_key in ("account_id", "mask"):
                    bad_source["actor"][event_key] = value
                else:
                    bad_source[event_key] = value
                bad_marker[marker_key] = value
                self.assertFalse(r.protection_valid(
                    bad_source, bad_marker, 301))
                self.assertFalse(r.can_dispatch(
                    None, bad_source, bad_marker, cord_id=301,
                    day=3, hour=11, hound_account_id=101,
                    hound_mask_id=201)[0])
                state, food, served, _reason = serve(
                    protection=bad_source, marker=bad_marker)
                self.assertFalse(served)
                self.assertIsNone(state)
                self.assertEqual(food, soup_state.pantry(None, 3))

    def test_signed_original_cord_required(self):
        source, marker, _, _ = fixture()
        self.assertTrue(r.protection_valid(source, marker, 301))
        self.assertFalse(r.protection_valid(source, marker, 302))
        for field, value in (("status", "consequence_failed"),
                             ("kind", "village.route_inspected")):
            bad = copy.deepcopy(source)
            bad[field] = value
            self.assertFalse(r.protection_valid(bad, marker, 301))
        bad = copy.deepcopy(source)
        bad["consequence"]["caution_marked"] = False
        self.assertFalse(r.protection_valid(bad, marker, 301))
        bad = copy.deepcopy(source)
        bad["actor"]["account_id"] = 999
        self.assertFalse(r.protection_valid(bad, marker, 301))

    def test_dispatch_one_per_day_and_clock_rewind(self):
        source, marker, _, _ = fixture()
        args = dict(cord_id=301, day=3, hour=11,
                    hound_account_id=101, hound_mask_id=201)
        self.assertTrue(r.can_dispatch(None, source, marker, **args)[0])
        self.assertFalse(r.can_dispatch({"day": 3}, source, marker, **args)[0])
        self.assertFalse(r.can_dispatch({"day": 4}, source, marker, **args)[0])
        self.assertFalse(r.can_dispatch(None, source, marker,
                         **dict(args, day=2))[0])
        # A new day cannot reuse yesterday's physical warning as fresh work.
        self.assertFalse(r.can_dispatch({"day": 3}, source, marker,
                         **dict(args, day=4))[0])

    def test_corrupt_marker_day_cannot_create_dispatch_or_refuge_meal(self):
        source, marker, event, token = fixture()
        bad_markers = [
            dict(marker, day=4),  # forged advanced day, genuine day-3 event
            {key: value for key, value in marker.items() if key != "day"},
            *[dict(marker, day=value)
              for value in (None, False, True, "3", 3.0, 0, -1)],
        ]
        for altered in bad_markers:
            with self.subTest(marker=altered):
                self.assertFalse(r.protection_valid(source, altered, 301))
                allowed, _why = r.can_dispatch(
                    {"day": 3}, source, altered, cord_id=301,
                    day=4, hour=11, hound_account_id=101,
                    hound_mask_id=201)
                self.assertFalse(allowed)  # no physical dispatch token
                history, pantry, served, _why = serve(marker=altered)
                self.assertFalse(served)  # no Tavern meal or pantry mutation
                self.assertIsNone(history)
                self.assertEqual(pantry, soup_state.pantry(None, 3))

        # Even a fresh private look at the inconsistent day-4 marker cannot
        # turn the real old day-3 event into a completed day-4 warning.
        seen = {"red_cord": {
            "day": 4, "hour": 11, "route_caution_event_id": 41,
            "route_caution_cord_id": 301}}
        self.assertTrue(observed_caution(
            seen, day=4, hour=11, source_event_id=41, cord_id=301))
        self.assertFalse(r.can_dispatch(
            {"day": 3}, source, dict(marker, day=4), cord_id=301,
            day=4, hour=11, hound_account_id=101,
            hound_mask_id=201)[0])

    def test_signed_retying_preserves_day_and_prior_source_chain(self):
        source, marker, dispatch, token = fixture()
        renewed = copy.deepcopy(source)
        renewed["id"] = 44
        renewed["payload"].update(day=4, prior_caution_event_id=41)
        renewed["consequence"].update(day=4, prior_caution_event_id=41)
        tied = dict(marker, event_id=44, day=4, prior_caution_event_id=41)
        self.assertTrue(r.protection_valid(renewed, tied, 301))
        self.assertTrue(r.can_dispatch(
            {"day": 3, "event_id": 42, "account_id": 101, "item_id": 401},
            renewed, tied, cord_id=301, day=4, hour=11,
            hound_account_id=101, hound_mask_id=201)[0])

        # An authentic day-4 dispatch and token must cite the new protection.
        next_dispatch = copy.deepcopy(dispatch)
        next_dispatch["id"] = 45
        next_dispatch["payload"].update(
            day=4, source_protect_event_id=44)
        next_dispatch["consequence"]["source_protect_event_id"] = 44
        next_token = dict(
            token, day=4, dispatch_event_id=45,
            source_protect_event_id=44)
        self.assertTrue(r.dispatch_valid(
            next_dispatch, next_token, renewed, tied, 301, 401))
        self.assertFalse(r.dispatch_valid(
            next_dispatch, next_token, source, marker, 301, 401))

        for bad in (
            dict(tied, prior_caution_event_id=42),
            dict(tied, prior_caution_event_id=True),
            {key: value for key, value in tied.items()
             if key != "prior_caution_event_id"},
        ):
            with self.subTest(bad=bad):
                self.assertFalse(r.protection_valid(renewed, bad, 301))
        changed = copy.deepcopy(renewed)
        changed["consequence"]["day"] = 3
        self.assertFalse(r.protection_valid(changed, tied, 301))
        changed = copy.deepcopy(renewed)
        changed["payload"]["prior_caution_event_id"] = 999
        self.assertFalse(r.protection_valid(changed, tied, 301))

    def test_malformed_prior_dispatch_record_cannot_authorize_new_work(self):
        # A persisted last-dispatch record is a signed physical consequence.
        # A day alone is not proof that a valid earlier dispatch existed.
        source, marker, _dispatch, _token = fixture()
        renewed = copy.deepcopy(source)
        renewed["id"] = 44
        renewed["payload"].update(day=4, prior_caution_event_id=41)
        renewed["consequence"].update(day=4, prior_caution_event_id=41)
        current = dict(marker, day=4, event_id=44,
                       prior_caution_event_id=41)
        args = dict(cord_id=301, day=4, hour=11,
                    hound_account_id=101, hound_mask_id=201)
        prior = {"day": 3, "event_id": 42,
                 "account_id": 101, "item_id": 401}
        self.assertTrue(r.can_dispatch(prior, renewed, current, **args)[0])
        self.assertFalse(r.can_dispatch(dict(prior, day=4),
                                        renewed, current, **args)[0])
        for key in ("day", "event_id", "account_id", "item_id"):
            missing = dict(prior)
            del missing[key]
            with self.subTest(missing=key):
                self.assertFalse(r.can_dispatch(
                    missing, renewed, current, **args)[0])
            for value in (None, False, True, 0, -1, 3.5, "3.5"):
                with self.subTest(field=key, value=value):
                    corrupted = dict(prior, **{key: value})
                    self.assertFalse(r.can_dispatch(
                        corrupted, renewed, current, **args)[0])
        # The gate does not allocate a physical token or spend soup stock.
        self.assertEqual(soup_state.pantry(None, 4)["stock"]["turnip"], 3)

    def test_valid_old_dispatch_survives_next_day_signed_retying(self):
        # Day 3, 23:00: one Hound signs and carries the physical dispatch.
        # Day 4, 10:00: another valid protection replaces the cord marker.
        # Day 4, 11:00: a distinct Innkeep can still spend a real meal.
        old, original, dispatch, token = fixture()
        old["payload"]["hour"] = 22
        dispatch["payload"]["hour"] = 23
        token["hour"] = 23
        renewed = copy.deepcopy(old)
        renewed["id"] = 44
        renewed["payload"].update(day=4, hour=10, prior_caution_event_id=41)
        renewed["consequence"].update(day=4, prior_caution_event_id=41)
        current = dict(original, event_id=44, day=4,
                       prior_caution_event_id=41)
        history = [copy.deepcopy(original)]
        selected = r.dispatch_source_marker(
            current, history, old, renewed, 301)
        self.assertEqual(selected, original)
        self.assertTrue(r.dispatch_valid(
            dispatch, token, old, selected, 301, 401))
        self.assertFalse(r.dispatch_valid(
            dispatch, token, old, current, 301, 401))
        saved = json.loads(json.dumps(dict(
            current=current, history=history, old=old, renewed=renewed)))
        selected = r.dispatch_source_marker(
            saved["current"], saved["history"], saved["old"],
            saved["renewed"], 301)
        self.assertEqual(selected, original)
        state, food, allowed, reason = serve(
            day=4, hour=11, protection=old, dispatch_event=dispatch,
            token=token, marker=selected)
        self.assertTrue(allowed, reason)
        self.assertEqual(food["stock"]["turnip"], 2)
        self.assertEqual(food["stock"]["salt"], 3)
        self.assertEqual(state["history"][0]["source_protect_event_id"], 41)
        # A restart cannot consume the same signed dispatch a second time.
        self.assertFalse(serve(
            raw=json.loads(json.dumps(state)),
            pantry_raw=json.loads(json.dumps(food)),
            day=4, hour=11, protection=old, dispatch_event=dispatch,
            token=token, marker=selected, event_id=46)[2])

    def test_saver_wrapped_old_dispatch_survives_retying_and_replay_denial(self):
        # Real Evennia attributes may reload as saver-backed mappings/lists.
        # The original physical dispatch remains valid after a next-day
        # signed cord re-tying, but it cannot spend a second pantry serving.
        old, original, dispatch, token = fixture()
        old["payload"]["hour"] = 22
        dispatch["payload"]["hour"] = 23
        token["hour"] = 23
        renewed = copy.deepcopy(old)
        renewed["id"] = 44
        renewed["payload"].update(day=4, hour=10, prior_caution_event_id=41)
        renewed["consequence"].update(day=4, prior_caution_event_id=41)
        current = dict(original, event_id=44, day=4,
                       prior_caution_event_id=41)
        restored = json.loads(json.dumps({
            "old": old, "original": original, "dispatch": dispatch,
            "token": token, "renewed": renewed, "current": current,
        }))
        current_saved = UserDict(restored["current"])
        archived_saved = UserList([UserDict(restored["original"])])
        old_saved = UserDict(restored["old"])
        renewed_saved = UserDict(restored["renewed"])
        selected = r.dispatch_source_marker(
            current_saved, archived_saved, old_saved, renewed_saved, 301)
        self.assertEqual(selected["event_id"], 41)
        state, food, allowed, why = serve(
            day=4, hour=11, protection=old_saved,
            dispatch_event=UserDict(restored["dispatch"]),
            token=UserDict(restored["token"]), marker=selected)
        self.assertTrue(allowed, why)
        self.assertEqual(food["stock"]["turnip"], 2)
        self.assertEqual(food["stock"]["salt"], 3)
        self.assertEqual(state["history"][0]["source_protect_event_id"], 41)
        saved_state = UserDict({
            "history": UserList([UserDict(state["history"][0])])})
        saved_food = json.loads(json.dumps(food))
        replay_state, replay_food, replay_ok, _ = serve(
            raw=saved_state, pantry_raw=saved_food, day=4, hour=11,
            protection=old_saved, dispatch_event=restored["dispatch"],
            token=restored["token"], marker=selected, event_id=46)
        self.assertFalse(replay_ok)
        self.assertIsNone(replay_state)
        self.assertEqual(replay_food, saved_food)

        # A corrupted persisted physical archive must not authorize the
        # historical dispatch even when today's current marker is signed.
        bad_archive = UserList([
            UserDict(dict(restored["original"], event_id=999))])
        self.assertIsNone(r.dispatch_source_marker(
            current_saved, bad_archive, old_saved, renewed_saved, 301))
        before = soup_state.pantry(None, 4)
        denied_state, denied_food, denied, _ = serve(
            day=4, hour=11, protection=old_saved,
            dispatch_event=restored["dispatch"], token=restored["token"],
            marker=None)
        self.assertFalse(denied)
        self.assertIsNone(denied_state)
        self.assertEqual(denied_food, before)

    def test_historical_marker_forgery_and_missing_archive_fail_closed(self):
        old, original, dispatch, token = fixture()
        renewed = copy.deepcopy(old)
        renewed["id"] = 44
        renewed["payload"].update(day=4, prior_caution_event_id=41)
        renewed["consequence"].update(day=4, prior_caution_event_id=41)
        current = dict(original, event_id=44, day=4,
                       prior_caution_event_id=41)
        bad_cases = [
            (current, None, renewed),
            (current, [], renewed),
            (current, [dict(original, event_id=999)], renewed),
            (current, [dict(original, day=4)], renewed),
            (dict(current, prior_caution_event_id=999), [original], renewed),
            (dict(current, event_id=999), [original], renewed),
            (dict(current, day=3), [original], renewed),
            (current, [original], dict(renewed, status="consequence_failed")),
            (current, [original], dict(renewed, kind="village.route_inspected")),
            (current, "forged", renewed),
        ]
        for marker, history, current_event in bad_cases:
            with self.subTest(marker=marker, history=history):
                selected = r.dispatch_source_marker(
                    marker, history, old, current_event, 301)
                self.assertIsNone(selected)
                before = soup_state.pantry(None, 4)
                state, after, allowed, _ = serve(
                    day=4, hour=11, protection=old, dispatch_event=dispatch,
                    token=token, marker=selected)
                self.assertFalse(allowed)
                self.assertIsNone(state)
                self.assertEqual(after, before)
        self.assertIsNone(r.dispatch_source_marker(
            current, [original], dict(old, status="consequence_failed"),
            renewed, 301))
        self.assertIsNone(r.dispatch_source_marker(
            current, [original], old, renewed, 302))

    def test_forged_dispatch_source_or_item_rejected(self):
        source, marker, event, token = fixture()
        self.assertTrue(r.dispatch_valid(event, token, source, marker, 301, 401))
        for change in ({"status": "consequence_failed"},
                       {"kind": "village.route_inspected"}):
            self.assertFalse(serve(dispatch_event=dict(event, **change))[2])
        bad = copy.deepcopy(event)
        bad["actor"]["account_id"] = 999
        self.assertFalse(serve(dispatch_event=bad)[2])
        bad = copy.deepcopy(event)
        bad["consequence"]["item_id"] = 999
        self.assertFalse(serve(dispatch_event=bad)[2])
        self.assertFalse(serve(token_id=402)[2])
        self.assertFalse(serve(token=dict(token, source_protect_event_id=999))[2])
        self.assertFalse(serve(protection=dict(source, id=999))[2])

    def test_dispatch_completed_consequence_must_name_original_cord(self):
        # A valid request and physical token cannot authenticate an event
        # whose completed consequence cites another or no physical cord.
        source, marker, dispatch, token = fixture()
        self.assertTrue(r.dispatch_valid(
            dispatch, token, source, marker, 301, 401))
        for bad_id in (None, False, True, 0, 302, 301.9, "301.9"):
            with self.subTest(consequence_cord_id=bad_id):
                corrupt = copy.deepcopy(dispatch)
                corrupt["consequence"]["cord_id"] = bad_id
                self.assertFalse(r.dispatch_valid(
                    corrupt, token, source, marker, 301, 401))
                state, food, allowed, _ = serve(dispatch_event=corrupt)
                self.assertFalse(allowed)
                self.assertIsNone(state)
                self.assertEqual(food, soup_state.pantry(None, 3))
        missing = copy.deepcopy(dispatch)
        del missing["consequence"]["cord_id"]
        self.assertFalse(serve(dispatch_event=missing)[2])

        # The rule still permits a real signed dispatch served next day.
        source["payload"]["hour"] = 22
        dispatch["payload"]["hour"] = 23
        token["hour"] = 23
        state, food, allowed, why = serve(
            day=4, hour=11, protection=source, marker=marker,
            dispatch_event=dispatch, token=token)
        self.assertTrue(allowed, why)
        self.assertEqual(state["history"][0]["source_protect_event_id"], 41)
        self.assertEqual(food["stock"]["turnip"], 2)

    def test_transaction_rejects_mid_action_account_or_mask_swap(self):
        # Preview identities must still control each mask when the signed
        # consequence commits. A role check alone is insufficient.
        self.assertTrue(r.same_actor(101, 201, 101, 201))
        self.assertTrue(r.same_actor(102, 202, 102, 202))
        for changed in (
            (999, 201, 101, 201),  # Hound account changed
            (101, 999, 101, 201),  # Hound mask changed
            (999, 202, 102, 202),  # Innkeep account changed
            (102, 999, 102, 202),  # Innkeep mask changed
            (None, 201, 101, 201),  # Hound disconnected
            (None, 202, 102, 202),  # Innkeep disconnected
            (True, 201, 101, 201),
            ("101", 201, 101, 201),
            (101, "201", 101, 201),
        ):
            with self.subTest(changed=changed):
                self.assertFalse(r.same_actor(*changed))

    def test_same_account_role_switch_and_wrong_carrier(self):
        self.assertFalse(serve(innkeep_account_id=101)[2])
        self.assertFalse(serve(hound_account_id=999)[2])
        self.assertFalse(serve(hound_mask_id=999)[2])
        self.assertFalse(serve(innkeep_mask_id=True)[2])

    def test_duplicate_dispatch_rejected(self):
        history, food, ok, _ = serve()
        self.assertTrue(ok)
        self.assertFalse(serve(raw=history, pantry_raw=food, event_id=44)[2])

    def test_late_arrival_future_and_clock_rewind(self):
        self.assertTrue(serve(day=4, hour=11)[2])
        self.assertFalse(serve(day=4, hour=12)[2])
        self.assertFalse(serve(day=3, hour=10)[2])
        self.assertFalse(serve(day=0, hour=12)[2])
        self.assertFalse(serve(day=3, hour=True)[2])
        self.assertFalse(serve(day=3, hour=24)[2])

    def test_depleted_pantry_and_solo_fallback(self):
        pantry = soup_state.pantry(None, 3)
        pantry["stock"]["turnip"] = 0
        self.assertFalse(serve(pantry_raw=pantry)[2])
        self.assertEqual(soup_state.pantry(None, 3)["stock"]["turnip"], 3)
        self.assertTrue(soup_state.reserve(None, 3, "barley", "thyme")[1])

    def test_pre_marker_same_hour_cannot_authorize_firsthand_dispatch(self):
        # Two accounts: A looks before B physically signs the original cord.
        # Clock equality is not event-order evidence. A must look again.
        a_look = {"red_cord": {"day": 3, "hour": 10}}
        b_marker = 41
        self.assertFalse(observed_caution(
            a_look, day=3, hour=10, source_event_id=b_marker, cord_id=301))
        a_look["red_cord"].update(
            route_caution_event_id=b_marker, route_caution_cord_id=301)
        self.assertTrue(observed_caution(
            a_look, day=3, hour=10, source_event_id=b_marker, cord_id=301))
        for altered in (
            dict(a_look["red_cord"], route_caution_event_id=42),
            dict(a_look["red_cord"], route_caution_cord_id=302),
            dict(a_look["red_cord"], day=2),
            dict(a_look["red_cord"], hour=11),
            dict(a_look["red_cord"], route_caution_event_id=True),
        ):
            self.assertFalse(observed_caution(
                {"red_cord": altered}, day=3, hour=10,
                source_event_id=b_marker, cord_id=301))
        # A's current view must also survive a real persistence encoding.
        restored = json.loads(json.dumps(a_look))
        self.assertTrue(observed_caution(
            restored, day=3, hour=10, source_event_id=b_marker, cord_id=301))

    def test_restart_json_roundtrip(self):
        history, food, ok, _ = serve()
        self.assertTrue(ok)
        history = json.loads(json.dumps(history))
        food = json.loads(json.dumps(food))
        self.assertFalse(serve(raw=history, pantry_raw=food, event_id=44)[2])
        self.assertIn("1 signed Hound arrival", r.public_lines(history))
        self.assertIn("No witnessed", r.public_lines(None))

    def test_evennia_style_mutable_sequence_and_mapping_survive(self):
        history, food, ok, _ = serve()
        self.assertTrue(ok)
        saved = UserDict({"history": UserList([UserDict(history["history"][0])])})
        self.assertEqual(len(r.history(saved)), 1)
        self.assertIn("1 signed Hound arrival", r.public_lines(saved))
        self.assertFalse(serve(raw=saved, pantry_raw=food, event_id=44)[2])

    def test_corrupt_persisted_history_fails_closed(self):
        self.assertFalse(serve(raw={"history": [{"event_id": True}]})[2])
        self.assertFalse(serve(raw={"history": "forged"})[2])
        self.assertFalse(serve(raw="forged")[2])
        self.assertIn("requires inspection",
                      r.public_lines({"history": [{"event_id": True}]}))


if __name__ == "__main__":
    unittest.main()
