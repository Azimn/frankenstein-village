"""
Scripts

Scripts are powerful jacks-of-all-trades. They have no in-game
existence and can be used to represent persistent game systems in some
circumstances. Scripts can also have a time component that allows them
to "fire" regularly or a limited number of times.

There is generally no "tree" of Scripts inheriting from each other.
Rather, each script tends to inherit from the base Script class and
just overloads its hooks to have it perform its function.

"""

from pathlib import Path

from evennia.scripts.scripts import DefaultScript

REPO_ROOT = Path(__file__).resolve().parents[3]


class Script(DefaultScript):
    """
    This is the base TypeClass for all Scripts. Scripts describe
    all entities/systems without a physical existence in the game world
    that require database storage (like an economic system or
    combat tracker). They
    can also have a timer/ticker component.

    A script type is customized by redefining some or all of its hook
    methods and variables.

    * available properties (check docs for full listing, this could be
      outdated).

     key (string) - name of object
     name (string)- same as key
     aliases (list of strings) - aliases to the object. Will be saved
              to database as AliasDB entries but returned as strings.
     dbref (int, read-only) - unique #id-number. Also "id" can be used.
     date_created (string) - time stamp of object creation
     permissions (list of strings) - list of permission strings

     desc (string)      - optional description of script, shown in listings
     obj (Object)       - optional object that this script is connected to
                          and acts on (set automatically by obj.scripts.add())
     interval (int)     - how often script should run, in seconds. <0 turns
                          off ticker
     start_delay (bool) - if the script should start repeating right away or
                          wait self.interval seconds
     repeats (int)      - how many times the script should repeat before
                          stopping. 0 means infinite repeats
     persistent (bool)  - if script should survive a server shutdown or not
     is_active (bool)   - if script is currently running

    * Handlers

     locks - lock-handler: use locks.add() to add new lock strings
     db - attribute-handler: store/retrieve database attributes on this
                        self.db.myattr=val, val=self.db.myattr
     ndb - non-persistent attribute handler: same as db but does not
                        create a database entry when storing data

    * Helper methods

     create(key, **kwargs)
     start() - start script (this usually happens automatically at creation
               and obj.script.add() etc)
     stop()  - stop script, and delete it
     pause() - put the script on hold, until unpause() is called. If script
               is persistent, the pause state will survive a shutdown.
     unpause() - restart a previously paused script. The script will continue
                 from the paused timer (but at_start() will be called).
     time_until_next_repeat() - if a timed script (interval>0), returns time
                 until next tick

    * Hook methods (should also include self as the first argument):

     at_script_creation() - called only once, when an object of this
                            class is first created.
     is_valid() - is called to check if the script is valid to be running
                  at the current time. If is_valid() returns False, the running
                  script is stopped and removed from the game. You can use this
                  to check state changes (i.e. an script tracking some combat
                  stats at regular intervals is only valid to run while there is
                  actual combat going on).
      at_start() - Called every time the script is started, which for persistent
                  scripts is at least once every server start. Note that this is
                  unaffected by self.delay_start, which only delays the first
                  call to at_repeat().
      at_repeat() - Called every self.interval seconds. It will be called
                  immediately upon launch unless self.delay_start is True, which
                  will delay the first call of this method by self.interval
                  seconds. If self.interval==0, this method will never
                  be called.
      at_pause()
      at_stop() - Called as the script object is stopped and is about to be
                  removed from the game, e.g. because is_valid() returned False.
      at_script_delete()
      at_server_reload() - Called when server reloads. Can be used to
                  save temporary variables you want should survive a reload.
      at_server_shutdown() - called at a full server shutdown.
      at_server_start()

    """

    pass


class SpikeScript(DefaultScript):
    """Base class for village scripts: self-healing tickers.

    Scripts created via `evennia shell` start their tickers in the shell's
    process, not the server's. After a reload the server then sees
    is_active=True but has no task (ndb._task is None), and the normal
    pause/unpause cycle has no paused state to resume from — so the ticker
    silently never runs. This safety net starts it in-server on boot.
    (2026-10-02: every script ticker in the village was dead this way.)
    """

    def at_server_start(self):
        # Fresh ticker, unconditionally. A script created via `evennia shell`
        # starts its ticker in the shell's process; after the shell exits
        # the server can see a phantom ndb task (or none at all) while the
        # ticker silently never runs. Stopping any existing task and starting
        # anew guarantees the LoopingCall is bound to a live instance in
        # this process. (2026-10-04: village_routine's ticker was dead this
        # way — present and "running" per ndb, never firing.)
        if not self.is_active:
            return
        self._stop_task()
        self.start()


class AmbientLife(SpikeScript):
    """Ticking ambient life for the spike, from canon ambient-events v0.1.

    Every few minutes (irregularly), one observable happening from the
    canon file is emitted to the room it belongs to — a bell, a cat, a
    guttering candle. No mechanics, no choices; seeds for gossip. Rooms
    that currently hold players are preferred, so the life lands where
    someone can witness it.
    """

    # Canon sections mapped onto spike rooms. Sections for locations the
    # spike doesn't have yet (manor, marshes, ...) are skipped.
    SECTION_ROOMS = {
        "tavern & the inn": ["The Blood of the Vine", "Inn Common Room"],
        "well & the square": ["Village Square"],
    }

    def at_script_creation(self):
        self.key = "ambient_life"
        self.desc = "Canon ambient events, ticking."
        self.interval = 150
        self.persistent = True

    def _load_events(self):
        """Parse {room_key: [event texts]} out of the canon markdown."""
        import re

        path = REPO_ROOT / "files" / "ambient-events-v0.1.md"
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return {}
        events = {}
        current_rooms = []
        entry_re = re.compile(r"^\*\*(\d+)\.\*\*\s*(.+?)\s*—\s*\*Seen by:\*", re.M)
        for line in text.splitlines():
            m = re.match(r"^##\s+(.+?)\s*\(\d+[–-]\d+\)\s*$", line)
            if m:
                section = m.group(1).lower()
                current_rooms = []
                for key, rooms in self.SECTION_ROOMS.items():
                    if key in section:
                        current_rooms = rooms
                        break
                continue
            m = entry_re.match(line)
            if m and current_rooms:
                body = m.group(2).strip()
                for room_key in current_rooms:
                    events.setdefault(room_key, []).append(body)
        return events

    def at_repeat(self):
        import random
        from evennia.utils import search

        # Irregular rhythm: roughly two out of three ticks speak.
        if random.random() > 0.65:
            return
        events = self._load_events()
        if not events:
            return
        candidates = []
        for room_key, texts in events.items():
            found = [o for o in search.search_object(room_key) if o.key == room_key]
            if not found or not texts:
                continue
            room = found[0]
            players = sum(1 for o in room.contents if o.has_account)
            # Weight rooms with witnesses; empty rooms still tick quietly.
            candidates.extend([room] * (1 + 3 * players))
        if not candidates:
            return
        room = random.choice(candidates)
        text = random.choice(events[room.key])
        room.msg_contents(text)


class RoomSixMystery(DefaultScript):
    """Materialized world flags for Room Six. No ticker.

    Canonical causal history lives in WorldEventLedger; these flags are the
    fast projection used by the current gameplay code.

    db.m_told_by: key of the first player who gave the note to M.
    db.tavern_told_by: key of the first player who let the Tavern hear it.
    Per-player stages live on the characters themselves (db.room_six).
    """

    def at_script_creation(self):
        self.key = "room_six"
        self.desc = "Room Six mystery: world flags."
        self.interval = -1
        self.persistent = True


class ModerationQueue(DefaultScript):
    """Persistent, human-reviewed compact moderation.

    A player report is only an allegation. Reports never punish anyone by
    themselves. A human staff account must explicitly dismiss, warn, or ban.
    Every staff action is append-only and appealable from the account layer.
    """

    def at_script_creation(self):
        self.key = "moderation_queue"
        self.desc = "Human-reviewed compact reports and moderation audit trail."
        self.interval = -1
        self.persistent = True
        if self.db.reports is None:
            self.db.reports = []
        if self.db.next_report_id is None:
            self.db.next_report_id = 1
        if self.db.actions is None:
            self.db.actions = []
        if self.db.next_action_id is None:
            self.db.next_action_id = 1
        if self.db.appeals is None:
            self.db.appeals = []
        if self.db.next_appeal_id is None:
            self.db.next_appeal_id = 1

    @staticmethod
    def _account(account_id):
        if not account_id:
            return None
        from evennia.accounts.models import AccountDB

        try:
            return AccountDB.objects.get(id=account_id)
        except AccountDB.DoesNotExist:
            return None

    @staticmethod
    def _reviewer_fields(reviewer_account):
        return {
            "reviewed_by": reviewer_account.key,
            "reviewed_by_id": reviewer_account.id,
        }

    def _save_report(self, report):
        reports = list(self.db.reports or [])
        for index, current in enumerate(reports):
            if current.get("id") == report.get("id"):
                reports[index] = dict(report)
                self.db.reports = reports
                return dict(report)
        return None

    def _record_action(
        self,
        kind,
        reviewer_account,
        *,
        report_id=None,
        target_account_id=None,
        note="",
        related_action_id=None,
        appeal_id=None,
    ):
        import time

        actions = list(self.db.actions or [])
        action = {
            "id": int(self.db.next_action_id or 1),
            "kind": kind,
            "created_at": time.time(),
            "report_id": report_id,
            "target_account_id": target_account_id,
            "note": (note or "").strip(),
            "related_action_id": related_action_id,
            "appeal_id": appeal_id,
            "active": kind in {"warning", "ban"},
        }
        action.update(self._reviewer_fields(reviewer_account))
        self.db.next_action_id = action["id"] + 1
        actions.append(action)
        self.db.actions = actions
        return dict(action)

    def _action(self, action_id):
        for action in self.db.actions or []:
            if action.get("id") == action_id:
                return dict(action)
        return None

    def _set_action_active(self, action_id, active):
        actions = list(self.db.actions or [])
        for action in actions:
            if action.get("id") == action_id:
                action["active"] = bool(active)
                self.db.actions = actions
                return dict(action)
        return None

    def submit(self, report):
        reports = list(self.db.reports or [])
        report = dict(report)
        report["id"] = int(self.db.next_report_id or 1)
        report["status"] = "open"
        self.db.next_report_id = report["id"] + 1
        reports.append(report)
        self.db.reports = reports
        return dict(report)

    def get_report(self, report_id):
        for report in self.db.reports or []:
            if report.get("id") == report_id:
                return dict(report)
        return None

    def open_reports(self):
        return [
            dict(report)
            for report in (self.db.reports or [])
            if report.get("status") == "open"
        ]

    def audit_actions(self, limit=20):
        return [dict(action) for action in (self.db.actions or [])[-limit:]]

    def _resolve_report(self, report_id, reviewer_account, status, note=""):
        import time

        report = self.get_report(report_id)
        if not report or report.get("status") != "open":
            return None
        report["status"] = status
        report["reviewed_at"] = time.time()
        report.update(self._reviewer_fields(reviewer_account))
        if note:
            report["review_note"] = note.strip()
        return self._save_report(report)

    def dismiss_report(self, report_id, reviewer_account, note=""):
        report = self._resolve_report(
            report_id, reviewer_account, "dismissed", note=note
        )
        if not report:
            return None
        self._record_action(
            "dismissal",
            reviewer_account,
            report_id=report_id,
            target_account_id=report.get("target_account_id"),
            note=note,
        )
        return report

    def close_report(self, report_id, reviewer_account):
        """Backward-compatible alias for a reviewed dismissal."""
        return self.dismiss_report(report_id, reviewer_account)

    def warn_report(self, report_id, reviewer_account, note=""):
        report = self.get_report(report_id)
        if not report or report.get("status") != "open":
            return None, "No open report has that id."
        target = self._account(report.get("target_account_id"))
        if not target:
            return None, "That report is not linked to a player account."

        action = self._record_action(
            "warning",
            reviewer_account,
            report_id=report_id,
            target_account_id=target.id,
            note=note,
        )
        warnings = list(target.db.compact_warning_actions or [])
        if action["id"] not in warnings:
            warnings.append(action["id"])
            target.db.compact_warning_actions = warnings
        notices = list(target.db.moderation_notices or [])
        notices.append(
            {
                "action_id": action["id"],
                "kind": "warning",
                "text": note.strip() or "A human moderator issued a compact warning.",
                "seen": False,
            }
        )
        target.db.moderation_notices = notices[-50:]
        self._resolve_report(report_id, reviewer_account, "warned", note=note)
        target.msg(
            f"Compact warning #{action['id']}: "
            f"{note.strip() or 'A human moderator issued a warning.'} "
            f"You may appeal with: appeal {action['id']} <reason>"
        )
        return action, None

    def ban_report(self, report_id, reviewer_account, note=""):
        report = self.get_report(report_id)
        if not report or report.get("status") != "open":
            return None, "No open report has that id."
        target = self._account(report.get("target_account_id"))
        if not target:
            return None, "That report is not linked to a player account."
        active_warnings = [
            action_id
            for action_id in (target.db.compact_warning_actions or [])
            if (self._action(action_id) or {}).get("active")
        ]
        if not active_warnings:
            return None, "A compact ban requires at least one active human-issued warning first."

        action = self._record_action(
            "ban",
            reviewer_account,
            report_id=report_id,
            target_account_id=target.id,
            note=note,
        )
        bans = list(target.db.compact_ban_actions or [])
        if action["id"] not in bans:
            bans.append(action["id"])
            target.db.compact_ban_actions = bans
        notices = list(target.db.moderation_notices or [])
        notices.append(
            {
                "action_id": action["id"],
                "kind": "ban",
                "text": note.strip() or "World entry was suspended after human review.",
                "seen": False,
            }
        )
        target.db.moderation_notices = notices[-50:]
        self._resolve_report(report_id, reviewer_account, "banned", note=note)
        target.msg(
            f"World entry suspended by human review, action #{action['id']}. "
            f"You may remain OOC and appeal with: appeal {action['id']} <reason>"
        )
        target.unpuppet_all()
        return action, None

    def active_actions_for(self, account_id):
        return [
            dict(action)
            for action in (self.db.actions or [])
            if action.get("target_account_id") == account_id
            and action.get("kind") in {"warning", "ban"}
            and action.get("active")
        ]

    def appeals_for(self, account_id):
        return [
            dict(appeal)
            for appeal in (self.db.appeals or [])
            if appeal.get("account_id") == account_id
        ]

    def submit_appeal(self, account, action_id, reason):
        import time

        action = self._action(action_id)
        if (
            not action
            or action.get("target_account_id") != account.id
            or action.get("kind") not in {"warning", "ban"}
            or not action.get("active")
        ):
            return None, "That is not an active moderation action on this account."
        for appeal in self.db.appeals or []:
            if (
                appeal.get("action_id") == action_id
                and appeal.get("account_id") == account.id
                and appeal.get("status") == "open"
            ):
                return None, f"Appeal #{appeal['id']} is already open for that action."

        appeals = list(self.db.appeals or [])
        appeal = {
            "id": int(self.db.next_appeal_id or 1),
            "created_at": time.time(),
            "account_id": account.id,
            "account_key": account.key,
            "action_id": action_id,
            "reason": reason.strip(),
            "status": "open",
        }
        self.db.next_appeal_id = appeal["id"] + 1
        appeals.append(appeal)
        self.db.appeals = appeals
        return dict(appeal), None

    def open_appeals(self):
        return [
            dict(appeal)
            for appeal in (self.db.appeals or [])
            if appeal.get("status") == "open"
        ]

    def resolve_appeal(self, appeal_id, reviewer_account, outcome, note=""):
        import time

        if outcome not in {"uphold", "overturn"}:
            return None, "Appeal outcome must be uphold or overturn."
        appeals = list(self.db.appeals or [])
        selected = None
        for appeal in appeals:
            if appeal.get("id") == appeal_id and appeal.get("status") == "open":
                selected = appeal
                break
        if not selected:
            return None, "No open appeal has that id."

        action = self._action(selected.get("action_id"))
        if not action:
            return None, "The appealed moderation action no longer exists."

        target = self._account(action.get("target_account_id"))
        if outcome == "overturn":
            self._set_action_active(action["id"], False)
            if target:
                if action.get("kind") == "warning":
                    target.db.compact_warning_actions = [
                        action_id
                        for action_id in (target.db.compact_warning_actions or [])
                        if action_id != action["id"]
                    ]
                elif action.get("kind") == "ban":
                    target.db.compact_ban_actions = [
                        action_id
                        for action_id in (target.db.compact_ban_actions or [])
                        if action_id != action["id"]
                    ]

        if target:
            notices = list(target.db.moderation_notices or [])
            notice_kind = (
                "appeal_overturned" if outcome == "overturn" else "appeal_upheld"
            )
            default_text = (
                "A human moderator overturned the action on appeal."
                if outcome == "overturn"
                else "A human moderator upheld the action on appeal."
            )
            notices.append(
                {
                    "action_id": action["id"],
                    "kind": notice_kind,
                    "text": note.strip() or default_text,
                    "seen": False,
                }
            )
            target.db.moderation_notices = notices[-50:]
            if outcome == "overturn":
                target.msg(
                    f"Appeal #{appeal_id} was granted. Moderation action "
                    f"#{action['id']} was overturned."
                )
            else:
                target.msg(
                    f"Appeal #{appeal_id} was reviewed and the moderation "
                    f"action #{action['id']} was upheld."
                )

        selected["status"] = "resolved"
        selected["outcome"] = outcome
        selected["resolved_at"] = time.time()
        selected["resolution_note"] = note.strip()
        selected.update(self._reviewer_fields(reviewer_account))
        self.db.appeals = appeals
        self._record_action(
            f"appeal_{outcome}",
            reviewer_account,
            target_account_id=action.get("target_account_id"),
            note=note,
            related_action_id=action.get("id"),
            appeal_id=appeal_id,
        )
        return dict(selected), None


class ResidentPopulationRegistry(DefaultScript):
    """Shared coordination state for the resident population.

    Character-specific mutable state never lives here. This script owns only
    cross-resident coordination: logical-place availability, fact claims, and
    aggregate instrumentation.
    """

    def at_script_creation(self):
        self.key = "resident_population"
        self.desc = "Resident population coordination and instrumentation."
        self.interval = -1
        self.persistent = True
        if self.db.location_states is None:
            self.db.location_states = {}
        if self.db.fact_claims is None:
            self.db.fact_claims = {}
        if self.db.metrics is None:
            self.db.metrics = {}




class RumorRegistry(DefaultScript):
    """Persistent rumor roots, transmissions, and per-actor belief updates.

    Root rumor records are immutable after creation. Every hearing or retelling
    creates a transmission record with a parent pointer. Actor belief stores
    only point at transmissions, so current belief and historical provenance
    remain separate.
    """

    def at_script_creation(self):
        self.key = "rumor_registry"
        self.desc = "Persistent rumor provenance and belief registry."
        self.interval = -1
        self.persistent = True
        if self.db.rumors is None:
            self.db.rumors = []
        if self.db.transmissions is None:
            self.db.transmissions = []
        if self.db.next_rumor_id is None:
            self.db.next_rumor_id = 1
        if self.db.next_transmission_id is None:
            self.db.next_transmission_id = 1

    @staticmethod
    def _actor_ref(actor):
        if actor is None:
            return None
        account = getattr(actor, "account", None)
        return {
            "key": getattr(actor, "key", None),
            "id": getattr(actor, "id", None),
            "kind": "player" if account else "npc",
            "account_id": getattr(account, "id", None) if account else None,
        }

    @staticmethod
    def _beliefs(actor):
        return dict(actor.db.rumor_beliefs or {})

    @staticmethod
    def _write_belief(actor, rumor_id, belief):
        beliefs = dict(actor.db.rumor_beliefs or {})
        beliefs[str(rumor_id)] = dict(belief)
        # Current belief is bounded while the immutable registry keeps history.
        if len(beliefs) > 40:
            oldest = sorted(
                beliefs.items(),
                key=lambda pair: pair[1].get("heard_at", 0),
            )[: len(beliefs) - 40]
            for key, _value in oldest:
                beliefs.pop(key, None)
        actor.db.rumor_beliefs = beliefs
        try:
            from world.residents import note_rumor_exposure
            note_rumor_exposure(actor, rumor_id)
        except Exception:
            pass
        return dict(belief)

    def beliefs_for(self, actor):
        return self._beliefs(actor)

    def belief_for(self, actor, rumor_id):
        belief = self._beliefs(actor).get(str(rumor_id))
        return dict(belief) if belief else None

    def ensure_rumor(
        self,
        *,
        subject,
        claim,
        source_actor,
        source_type,
        original_event_id,
        origin_location,
        confidence,
        emotional_charge,
        privacy,
        variants=None,
        canonical_seed_id=None,
        family=None,
    ):
        """Return an existing root for a stable identity or create one."""
        rumors = list(self.db.rumors or [])
        for rumor in rumors:
            if canonical_seed_id is not None and (
                rumor.get("canonical_seed_id") == canonical_seed_id
            ):
                return dict(rumor)
            if (
                original_event_id is not None
                and rumor.get("original_event_id") == original_event_id
                and rumor.get("subject") == subject
            ):
                return dict(rumor)
            if (
                canonical_seed_id is None
                and original_event_id is None
                and rumor.get("claim") == claim
                and rumor.get("source_type") == source_type
                and rumor.get("family") == (family or subject)
            ):
                return dict(rumor)

        import time

        rumor = {
            "id": int(self.db.next_rumor_id or 1),
            "subject": subject,
            "claim": claim,
            "source_actor": source_actor,
            "source_type": source_type,
            "original_event_id": original_event_id,
            "heard_at": time.time(),
            "heard_location": origin_location,
            "confidence": float(confidence),
            "emotional_charge": float(emotional_charge),
            "privacy": privacy,
            "distortion_generation": 0,
            "variants": list(variants or []),
            "canonical_seed_id": canonical_seed_id,
            "family": family or subject,
        }
        self.db.next_rumor_id = rumor["id"] + 1
        rumors.append(rumor)
        self.db.rumors = rumors
        return dict(rumor)

    def get_rumor(self, rumor_id):
        try:
            rumor_id = int(rumor_id)
        except (TypeError, ValueError):
            return None
        for rumor in self.db.rumors or []:
            if rumor.get("id") == rumor_id:
                return dict(rumor)
        return None

    def get_transmission(self, transmission_id):
        try:
            transmission_id = int(transmission_id)
        except (TypeError, ValueError):
            return None
        for transmission in self.db.transmissions or []:
            if transmission.get("id") == transmission_id:
                return dict(transmission)
        return None

    def _append_transmission(
        self,
        *,
        rumor,
        parent_id,
        speaker_ref,
        listener,
        claim,
        confidence,
        generation,
        location,
        accepted,
        source_type,
    ):
        import time

        transmissions = list(self.db.transmissions or [])
        record = {
            "id": int(self.db.next_transmission_id or 1),
            "rumor_id": rumor["id"],
            "parent_id": parent_id,
            "speaker": speaker_ref,
            "listener": self._actor_ref(listener),
            "claim": claim,
            "confidence": float(confidence),
            "emotional_charge": min(
                1.0,
                float(rumor.get("emotional_charge", 0.0))
                + (0.04 * int(generation or 0)),
            ),
            "heard_at": time.time(),
            "heard_location": location,
            "distortion_generation": int(generation or 0),
            "accepted": bool(accepted),
            "source_type": source_type,
        }
        self.db.next_transmission_id = record["id"] + 1
        transmissions.append(record)
        self.db.transmissions = transmissions
        return dict(record)

    def hear_direct(
        self,
        rumor_id,
        listener,
        *,
        source_label,
        source_type,
        location=None,
        force_new=False,
    ):
        """Record direct hearing from a root source or public institution."""
        rumor = self.get_rumor(rumor_id)
        if not rumor or listener is None:
            return None
        existing = self.belief_for(listener, rumor_id)
        if existing and not force_new:
            return existing

        record = self._append_transmission(
            rumor=rumor,
            parent_id=None,
            speaker_ref={
                "key": source_label,
                "id": None,
                "kind": source_type,
                "account_id": None,
            },
            listener=listener,
            claim=rumor["claim"],
            confidence=rumor["confidence"],
            generation=0,
            location=location,
            accepted=True,
            source_type=source_type,
        )
        belief = {
            "rumor_id": rumor["id"],
            "transmission_id": record["id"],
            "claim": record["claim"],
            "confidence": record["confidence"],
            "heard_from": source_label,
            "heard_at": record["heard_at"],
            "heard_location": location,
            "distortion_generation": 0,
        }
        return self._write_belief(listener, rumor["id"], belief)

    def transmit(
        self,
        rumor_id,
        speaker,
        listener,
        *,
        location=None,
        force_accept=False,
        force_variant_index=None,
        allow_private=False,
    ):
        """Retell a known rumor and append an immutable transmission."""
        rumor = self.get_rumor(rumor_id)
        if not rumor or speaker is None or listener is None:
            return None
        if rumor.get("privacy") != "public" and not allow_private:
            return None
        source_belief = self.belief_for(speaker, rumor_id)
        if not source_belief:
            return None
        parent = self.get_transmission(source_belief.get("transmission_id"))
        if not parent:
            return None

        import random

        generation = int(parent.get("distortion_generation") or 0) + 1
        claim = parent.get("claim") or rumor["claim"]
        variants = list(rumor.get("variants") or [])
        curiosity = float(speaker.db.rumor_curiosity or 0.5)
        mutate_p = min(0.6, 0.18 * (0.5 + curiosity))
        if variants:
            if force_variant_index is not None:
                index = max(0, min(int(force_variant_index), len(variants) - 1))
                claim = variants[index]
            elif random.random() < mutate_p:
                claim = random.choice(variants)

        confidence = min(
            1.0,
            float(parent.get("confidence") or rumor["confidence"])
            + 0.04
            + (0.06 * curiosity),
        )

        existing = self.belief_for(listener, rumor_id)
        gullibility = float(listener.db.rumor_gullibility or 0.5)
        accepted = True
        if existing and not force_accept:
            accepted = (
                confidence > float(existing.get("confidence") or 0.0) + 0.12
                or random.random() < gullibility
            )

        record = self._append_transmission(
            rumor=rumor,
            parent_id=parent["id"],
            speaker_ref=self._actor_ref(speaker),
            listener=listener,
            claim=claim,
            confidence=confidence,
            generation=generation,
            location=location,
            accepted=accepted,
            source_type="retelling",
        )

        if accepted:
            belief = {
                "rumor_id": rumor["id"],
                "transmission_id": record["id"],
                "claim": record["claim"],
                "confidence": record["confidence"],
                "heard_from": speaker.key,
                "heard_at": record["heard_at"],
                "heard_location": location,
                "distortion_generation": generation,
            }
            self._write_belief(listener, rumor["id"], belief)
        return record

    def provenance(self, transmission_id):
        """Return oldest-to-newest transmission chain."""
        chain = []
        current = self.get_transmission(transmission_id)
        seen = set()
        while current and current["id"] not in seen:
            seen.add(current["id"])
            chain.append(current)
            parent_id = current.get("parent_id")
            current = self.get_transmission(parent_id) if parent_id else None
        chain.reverse()
        return chain

    def known_by(self, rumor_id):
        """Return actor references for accepted hearings, without duplicates."""
        known = {}
        for transmission in self.db.transmissions or []:
            if (
                transmission.get("rumor_id") == rumor_id
                and transmission.get("accepted")
            ):
                listener = transmission.get("listener") or {}
                identity = (listener.get("kind"), listener.get("id"))
                known[identity] = dict(listener)
        return list(known.values())

    def current_claims(self, rumor_id):
        """Return distinct accepted claim variants currently represented."""
        return sorted(
            {
                transmission.get("claim")
                for transmission in self.db.transmissions or []
                if transmission.get("rumor_id") == rumor_id
                and transmission.get("accepted")
                and transmission.get("claim")
            }
        )



class WorldEventLedger(DefaultScript):
    """Canonical persistent event ledger for world changes."""

    def at_script_creation(self):
        self.key = "world_event_ledger"
        self.desc = "Canonical persistent event ledger."
        self.interval = -1
        self.persistent = True
        if self.db.events is None:
            self.db.events = []
        if self.db.next_event_id is None:
            self.db.next_event_id = 1

    def begin_event(self, event):
        events = list(self.db.events or [])
        event = dict(event)
        event["id"] = int(self.db.next_event_id or 1)
        event["status"] = "recorded"
        self.db.next_event_id = event["id"] + 1
        events.append(event)
        self.db.events = events
        return dict(event)

    def update_event(self, event_id, **fields):
        events = list(self.db.events or [])
        updated = None
        for index, event in enumerate(events):
            if event.get("id") != event_id:
                continue
            replacement = dict(event)
            replacement.update(fields)
            events[index] = replacement
            updated = replacement
            break
        if updated is not None:
            self.db.events = events
            return dict(updated)
        return None

    def get_event(self, event_id):
        for event in self.db.events or []:
            if event.get("id") == event_id:
                return dict(event)
        return None


_NUMWORDS = [
    "twelve", "one", "two", "three", "four", "five", "six", "seven",
    "eight", "nine", "ten", "eleven",
]


def village_hour_name(hour):
    """'nine of the evening' — the bell's vocabulary."""
    if hour == 0:
        return "midnight"
    if hour == 12:
        return "noon"
    if 1 <= hour <= 4:
        return f"{_NUMWORDS[hour]} of the small hours"
    if 5 <= hour <= 11:
        return f"{_NUMWORDS[hour]} of the morning"
    return f"{_NUMWORDS[hour - 12]} of the {'afternoon' if hour < 18 else 'evening'}"


class WarmthWatch(SpikeScript):
    """The body, prototyped: one internal variable with a voice.

    Jay's bladder principle (2026-09-29): the underlying variable and the
    perceived/narrated state are SEPARATE layers that may legitimately
    diverge (0.73 on the slider vs the felt urgency). Here: db.warmth is
    the runtime's number; _felt_band() is the narrator's words. They are
    aligned today; the split is architectural, so fever, fear, or drink
    can later move the feeling without touching the number.

    Rain + square drains; hearths restore. Threshold-crossing narration
    only — no mechanical penalties yet. This is the prototype the whole
    needs-slider architecture (hunger, fatigue) will follow.
    """

    ROOM_KEYS = (
        "Private Room", "Inn Common Room", "Inn Hallway",
        "Village Square", "The Blood of the Vine", "Tavern Back Hall",
    )

    def at_script_creation(self):
        self.key = "warmth_watch"
        self.desc = "The body's warmth, ticking."
        self.interval = 60
        self.persistent = True

    @staticmethod
    def _felt_band(warmth):
        if warmth >= 0.75:
            return "warm"
        if warmth >= 0.5:
            return "cool"
        if warmth >= 0.25:
            return "cold"
        return "freezing"

    @staticmethod
    def _band_line(band):
        return {
            "cool": "A chill settles into your shoulders.",
            "cold": "You are shivering.",
            "freezing": "The cold has settled into your bones. Find a hearth.",
            "warm": "Warmth spreads through you.",
        }.get(band)

    def _tick_char(self, char, room_key, weather):
        w = char.db.warmth
        if w is None:
            w = 1.0
        if room_key == "Village Square":
            if weather == "rain":
                w -= 0.08
            elif weather == "fog":
                w -= 0.03
            else:
                w -= 0.02
        elif room_key == "Inn Hallway":
            w -= 0.01
        else:
            # Private Room, Inn Common Room, The Tavern: hearths.
            w += 0.08
        w = max(0.0, min(1.0, w))
        char.db.warmth = w
        band = self._felt_band(w)
        old = char.db.warmth_band
        if old is None:
            # First sighting: calibrate silently.
            char.db.warmth_band = band
            return
        if old != band:
            char.db.warmth_band = band
            line = self._band_line(band)
            if line:
                char.msg(line)

    def at_repeat(self):
        from evennia.utils import search
        from evennia.scripts.models import ScriptDB

        try:
            weather = ScriptDB.objects.get(db_key="village_weather").db.state
        except Exception:
            weather = "clear"
        for key in self.ROOM_KEYS:
            found = [o for o in search.search_object(key) if o.key == key]
            if not found:
                continue
            for room in found:
                for char in room.contents:
                    if not char.has_account:
                        continue
                    self._tick_char(char, key, weather)


class VillageTime(SpikeScript):
    """The village clock. One game-hour per ten real minutes.

    Time is prosthetic memory for players whose context resets: the bell
    gives every session temporal landmarks worth writing down.
    """

    def at_script_creation(self):
        self.key = "village_time"
        self.desc = "The village clock."
        self.interval = 600
        self.persistent = True
        if self.db.hour is None:
            self.db.hour = 21  # the village starts at night
        if self.db.day is None:
            self.db.day = 1  # day counter; routines shift monthly on it

    def at_repeat(self):
        from evennia.utils import search

        # NOTE: do NOT write `(self.db.hour or 21)` — midnight is 0,
        # which is falsy, and the old expression jumped 0 -> 22 after
        # every midnight (caught by the 2026-10-03 lurker playtest).
        hour = self.db.hour
        if hour is None:
            hour = 21
        hour = (hour + 1) % 24
        self.db.hour = hour
        if hour == 0:
            self.db.day = (self.db.day or 1) + 1
        name = village_hour_name(hour)
        for key in ("Village Square", "The Blood of the Vine", "Inn Common Room",
                    "Inn Hallway", "Private Room", "Tavern Back Hall"):
            found = [o for o in search.search_object(key) if o.key == key]
            if not found:
                continue
            for room in found:
                if any(o.has_account for o in room.contents):
                    room.msg_contents(f"The village bell counts {name}.")


class VillageWeather(SpikeScript):
    """Weather over the square. Shifts every ~25 minutes, irregularly.

    The square's description has smelled of rain that hasn't fallen since
    the spike began. Now it falls.
    """

    WEATHER_SENSE = {
        "clear": "The night air is cold and clear.",
        "fog": "Fog deadens every sound; the gaslight is a smear.",
        "rain": "Rain drums on the cobbles; the smell of wet stone rises.",
    }
    ARRIVE_MSGS = {
        "clear": "The sky clears over the square.",
        "fog": "Fog rolls into the square, deadening every sound.",
        "rain": "Rain begins to fall on the square, hissing on the gaslight.",
    }
    LEAVE_MSGS = {
        "fog": "The fog thins over the square.",
        "rain": "The rain eases off over the square.",
    }

    def at_script_creation(self):
        self.key = "village_weather"
        self.desc = "Weather over the village square."
        self.interval = 1500
        self.persistent = True
        if not self.db.state:
            self.db.state = "fog"

    def set_weather(self, state):
        """Transition to `state`, announcing and updating the square."""
        from evennia.utils import search

        old = self.db.state
        if old == state:
            return
        self.db.state = state
        found = [o for o in search.search_object("Village Square")
                 if o.key == "Village Square"]
        if found:
            square = found[0]
            square.db.weather_sense = self.WEATHER_SENSE[state]
            leave = self.LEAVE_MSGS.get(old)
            arrive = self.ARRIVE_MSGS[state]
            msg = f"{leave} {arrive}" if leave else arrive
            square.msg_contents(msg)

    def at_repeat(self):
        import random

        old = self.db.state or "fog"
        # Weather lingers: half the time nothing changes.
        if random.random() < 0.5:
            return
        choices = [s for s in self.WEATHER_SENSE if s != old]
        self.set_weather(random.choice(choices))


class CatLife(SpikeScript):
    """The tavern cat's drives, ticking.

    Curiosity moves her between haunts; comfort keeps her there a while.
    She watches newcomers, performs small cattenings, and once in a blue
    moon does the wren thing (ambient-events #2). She never speaks — which
    is the point, except on the rarest of ticks, when she does, and that
    is also the point: not all residents need language to be alive, but
    the world is never 100% reliable, and the exceptions are what make
    players ask how much is scripted. A miracle with no witness is
    wasted, so the rarest beats only fire when players are present.
    """

    # Per effective tick (the quiet gate already passed). ~15 effective
    # ticks/hour of occupied time -> 1/800 lands roughly once every two
    # days of someone actually being there. Rare enough to be doubted.
    MIRACLE_CHANCE = 1 / 800

    def at_script_creation(self):
        self.key = "cat_life"
        self.desc = "The tavern cat, being a cat."
        self.interval = 110
        self.persistent = True

    def _miracle(self, loc, players):
        """One of the rare beats. Returns True if one fired."""
        import random

        from evennia.utils import create

        player = random.choice(players)
        roll = random.random()
        if roll < 0.34:
            # the gift: an inventory item, presented with ceremony
            mouse = create.create_object(
                "typeclasses.objects.Object",
                key="a dead mouse",
                location=player,
            )
            mouse.db.desc = (
                "A dead mouse, laid at your feet with terrible ceremony. "
                "The cat is watching to see what you do with it."
            )
            loc.msg_contents(
                f"The tavern cat pads to {player.key}, drops something "
                "small and still at their feet, and looks up — waiting."
            )
        elif roll < 0.67:
            # the word: she speaks, once, and denies it utterly
            loc.msg_contents(
                f"The tavern cat looks directly at {player.key} and says, "
                "quite clearly: \"Again.\" Then she begins washing her face "
                "with great dignity, as if nothing happened."
            )
        else:
            # the leading: she wants you to follow
            loc.msg_contents(
                "The tavern cat walks to the tavern door, stops, and looks "
                f"back at {player.key}. Waiting."
            )
        return True

    def at_repeat(self):
        import random

        cat = self.obj
        if not cat or not cat.location:
            return
        loc = cat.location
        # Quiet more often than not: a cat mostly sleeps.
        if random.random() > 0.55:
            return

        spots = cat.db.spots or ["the hearth"]
        spot = cat.db.spot or spots[0]
        players = [o for o in loc.contents if o.has_account and o != cat]

        # the miracle tier: checked first, fires almost never
        if players and random.random() < self.MIRACLE_CHANCE:
            self._miracle(loc, players)
            return

        roll = random.random()
        if roll < 0.35:
            # curiosity: relocate
            new_spot = random.choice([s for s in spots if s != spot] or spots)
            cat.db.spot = new_spot
            loc.msg_contents(
                f"The tavern cat pads from {spot} to {new_spot}."
            )
        elif roll < 0.55 and players:
            # watch someone
            watcher = random.choice(players)
            loc.msg_contents(
                f"The tavern cat watches {watcher.key} from {spot}, "
                "unblinking."
            )
        elif roll < 0.75:
            loc.msg_contents(
                random.choice([
                    f"The tavern cat stretches along {spot}, claws out, "
                    "then thinks better of it.",
                    f"The tavern cat washes one paw at {spot} with total "
                    "commitment.",
                    f"The tavern cat sleeps at {spot}. Her sides rise and "
                    "fall like a tiny bellows.",
                ])
            )
        elif roll < 0.93:
            loc.msg_contents(
                random.choice([
                    "The tavern cat chases a dust mote through a bar of "
                    "lamplight, misses, and sits down as if that was the "
                    "plan.",
                    "Somewhere under a table, the tavern cat purrs at "
                    "something only she can see.",
                ])
            )
        else:
            # the wren thing, rarely and without explanation
            loc.msg_contents(
                "The tavern cat carries something small and dark to the "
                "hearth, lays it precisely before the empty chair, and "
                "stares at it."
            )


class VillageRoutine(SpikeScript):
    """Daily routines for the tavern regulars.

    Every interval (one game-hour), each regular is moved to wherever
    their schedule — or an active deviation — says they should be, with
    an arrival/departure line in their own voice. Every 30 game-days one
    regular's hours shift permanently, via the event ledger.
    """

    def at_script_creation(self):
        self.key = "village_routine"
        self.desc = "Daily routines for the tavern regulars."
        self.interval = 600
        self.persistent = True

    def at_repeat(self):
        from world.routines import tick
        tick()


class TavernLife(SpikeScript):
    """Ambient life for the Blood of the Vine.

    Every interval, one beat: gossip, toasts, brooding, cross-talk, a
    regular eating or drinking through the real consumable pipeline, or
    Bram polishing. The room is mid-conversation when players arrive —
    the NPC pub doesn't need an audience.
    """

    def at_script_creation(self):
        self.key = "tavern_life"
        self.desc = "Ambient life in the Blood of the Vine."
        self.interval = 150
        self.persistent = True

    def at_repeat(self):
        from world.tavern_life import run_beat
        run_beat()
