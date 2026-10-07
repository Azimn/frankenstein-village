"""DM-Q-0001: The Wrong Trunk — Newcomer private mystery.

A newcomer receives luggage belonging to someone who supposedly reached
Frankenstein Village months ago. The trunk can be returned, examined, sold,
reported, or used to search for the missing owner.

Canonical status: Working content; does not alter canon.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional
from evennia import create_script

from evennia.scripts.models import ScriptDB

from .situations import (
    REGISTRY_KEY,
    STATE_ORDER,
)

if TYPE_CHECKING:
    from evennia import Objects
    from evennia.objects.objects import DefaultMUDObject


TRUNK_ID = "DM-Q-0001-WRONG-TRUNK"
TRUNK_KEY = "wrong trunk"


# =============================================================================
# STATE DEFINITIONS
# =============================================================================

TRUNK_STATE = {
    "dormant": 0,
    "surfaced": 1,
    "investigating": 2,
    "changing": 3,
    "resolved_locally": 4,
    "aftermath": 5,
}


# =============================================================================
# TRUNK OBJECT CLASS
# =============================================================================

class WrongTrunk(DefaultMUDObject):
    """The trunk itself: stateless container of evidence and provenance.

    The trunk's content is handled by the attached WrongTrunkSituation script.
    This object exists for physical interaction: searching, examining, moving.
    """

    keys = TRUNK_KEY
    short_desc = "A worn trunk with new labels over older initials."
    long_desc = (
        "This trunk bears your name or room number on the outside, but beneath "
        "the newer label you can see older initials in faded ink. The wood is "
        "well-used, with travel tags from places no one in this village knows "
        "well. A leather latch is secure but not locked with a key."
    )

    # =====================================================================
    # TRUNK CONTENT (physical items inside)
    # =====================================================================

    def at_creation(self):
        """Populate the trunk with canon evidence."""
        super().at_creation()

        # Create physical items inside the trunk
        # These are separate objects the player can search and examine

        # 1. Travel tag (physical evidence)
        tag = self.create_object(
            object_typeclass="DefaultMUDObject",
            key="old travel tag",
            location=self,
            short_desc="A faded paper tag with initials 'V.D.'",
            long_desc=(
                "A rectangular paper tag, worn at the edges. The initials "
                "'V.D.' are printed in faded black ink at the top, with a "
                "location code below that is too faded to read clearly. The "
                "tag was once pinned to a suitcase handle."
            ),
        )

        # 2. Personal object (identity hint)
        personal_item = self.create_object(
            object_typeclass="DefaultMUDObject",
            key="small silver locket",
            location=self,
            short_desc="A silver locket, tarnished and unadorned",
            long_desc=(
                "A simple oval locket, silver but tarnished from age. It has "
                "no engraving or inscription visible. The clasp is intact but "
                "shows the same wear as the trunk's latch: many openings and "
                "closings over months or years."
            ),
        )

        # 3. Receipt (documentary evidence)
        receipt = self.create_object(
            object_typeclass="DefaultMUDObject",
            key="travel receipt",
            location=self,
            short_desc="A receipt from a coach route",
            long_desc=(
                "A folded receipt from a coach that departed Borgo Pass three "
                "months ago. The passenger name line is blank; only a date, "
                "route number, and fare stamp remain. The paper is brittle at "
                "the corners."
            ),
        )

        # 4. Wear marks (environmental evidence)
        wear_marks = self.create_object(
            object_typeclass="DefaultMUDObject",
            key="wear marks",
            location=self,
            short_desc="Scuffs and marks on the trunk's surface",
            long_desc=(
                "The trunk's surface shows distinctive wear: a circular dent "
                "near the bottom, scuff marks consistent with being dragged "
                "across rough cobblestone, and a faint oil stain on the "
                "underside that suggests it was recently moved."
            ),
        )

        # 5. Registry entry (world state hook)
        self.db.trunk_registry_entry = {
            "initials": "V.D.",
            "arrival_date": "approximately 3 months ago",
            "claimed": False,
            "storage_location": "Inn Between storage",
            "notes": "Tagged and stored without incident until now.",
        }

    # =====================================================================
    # PLAYER INTERACTION
    # =====================================================================

    def at_enter(self, actor):
        """When the player first accesses the trunk."""
        if not hasattr(actor, "wrong_trunk_interacted"):
            actor.db.wrong_trunk_interacted = False

        if not actor.db.wrong_trunk_interacted:
            actor.db.wrong_trunk_interacted = True
            actor.msg(
                f"\n\nYou notice the trunk bears your label, but beneath it "
                "faded initials 'V.D.' are visible. The trunk feels heavier "
                "than expected."
            )

    def examine(self, actor):
        """Provide detailed examination text."""
        return self.long_desc


# =============================================================================
# SITUATION SCRIPT (quest state engine)
# =============================================================================

class WrongTrunkSituation:
    """Script-based situation engine for DM-Q-0001.

    This script tracks objective state, NPC beliefs, evidence discovery, and
    autonomous progression without freezing while the player is offline.
    """

    def __init__(self, trunk: WrongTrunk):
        self.trunk = trunk
        self.situation_id = TRUNK_ID
        self.state = "dormant"
        self.discovery_count = 0
        self.evidence_collected = set()
        self.player_interactions = []
        self.npc_beliefs = {
            "porter": "simple luggage error",
            "innkeeper": "remembers initials but not face",
            "harbinger_worker": "sees old classified notice with same initials",
            "resident_alice": "confidently remembers a different person entirely",
        }
        self.autonomy_deadline = None  # set by at_start

    # =====================================================================
    # AUTONOMOUS PROGRESSION
    # =====================================================================

    def at_start(self):
        """Initialize autonomous timeline and NPC belief state."""
        # Set deadline for autonomous progression (7 days in game time)
        self.autonomy_deadline = time.time() + 7 * 24 * 60 * 60  # 7 days
        self.state = "dormant"
        self.discovery_count = 0

        # Log initialization
        self.log_event("Situation initialized. State: dormant.")

    def at_interval(self, dt):
        """Check for autonomous progression every interval."""
        # Use a reasonable interval for server-side checks
        if dt > 60:  # every minute of simulated time
            if self.autonomy_deadline and time.time() >= self.autonomy_deadline:
                self.advance_autonomy()

    def advance_autonomy(self):
        """NPC actions occur when deadline passes."""
        if self.state != "dormant" and self.state != "surfaced":
            return

        # NPC: Innkeeper moves unclaimed luggage to storage
        self.log_event("Autonomous: Innkeeper moves trunk to long-term storage.")

        # Update trunk location state (could change location in-game)
        self.trunk.db.storage_status = "long_term"
        self.state = "changing"

        self.log_event(f"State advanced to: {self.state}")

    # =====================================================================
    # DISCOVERY TRACKING
    # =====================================================================

    def record_discovery(self, evidence_key: str, discoverer: "Objects"):
        """Track when a player discovers evidence."""
        if evidence_key not in self.evidence_collected:
            self.evidence_collected.add(evidence_key)
            self.discovery_count += 1
            self.player_interactions.append({
                "discovery": evidence_key,
                "discoverer": discoverer.key,
                "timestamp": time.time(),
            })
            self.log_event(f"Discovery: {discoverer.key} found {evidence_key}.")

    def get_discovery_summary(self, actor: "Objects") -> str:
        """Return a summary of what this player has discovered."""
        if not self.evidence_collected:
            return "You have not yet interacted with this trunk's contents."

        items = [
            f"• {item}"
            for item in sorted(self.evidence_collected)
        ]
        return "\n".join(items)

    # =====================================================================
    # NPC BELIEFS (separate from objective truth)
    # =====================================================================

    def get_npc_belief(self, npc_name: str) -> str:
        """Return how a specific NPC views the trunk."""
        return self.npc_beliefs.get(npc_name, "neutral")

    def log_event(self, message: str):
        """Log situation event to trunk.db for persistence and debugging."""
        if not hasattr(self.trunk, "situation_log"):
            self.trunk.db.situation_log = []
        self.trunk.db.situation_log.append({
            "event": message,
            "timestamp": time.time(),
            "state": self.state,
        })

    # =====================================================================
    # QUEST PROGRESSION HELPERS
    # =====================================================================

    def on_return_attempt(self, actor: "Objects", method: str = "direct") -> str:
        """Handle player attempt to return the trunk."""
        if method == "direct":
            return (
                "You take the trunk to the Innkeeper. They recognize the new label "
                "but hesitate at the older initials. 'This trunk... I've seen it "
                "before. Someone claimed it was lost months ago, but never came back.' "
                "They store it in long-term storage and note your name."
            )
        elif method == "via_harbinger":
            return (
                "You submit the trunk to the Harbinger office as found property. "
                "They create a public notice and forward it to the Innkeeper. "
                "This will attract potential claimants."
            )
        elif method == "public":
            return (
                "You post a public notice about the trunk. Several people respond, "
                "claiming to remember 'V.D.' from years ago. The notice will be "
                "printed in the next Harbinger."
            )
        return "Return attempt logged."

    def on_investigate(self, actor: "Objects") -> str:
        """Guide player through investigation pathways."""
        return (
            f"\n\nYou can investigate through several routes:\n\n"
            f"• Search the Inn Between storage logs\n"
            f"• Ask around about initials 'V.D.'\n"
            f"• Examine the trunk's contents more closely\n"
            f"• Report it as found property\n"
            f"• Keep it temporarily to inspect further\n"
        )

    def get_outcome_space(self) -> dict:
        """Return the possible outcome paths."""
        return {
            "return_immediate": {
                "label": "Return immediately",
                "consequence": "Earns trust but less information.",
            },
            "investigate": {
                "label": "Investigate",
                "consequence": "May expose private material and create future relationships.",
            },
            "publicize": {
                "label": "Publicize",
                "consequence": "Attracts multiple claimants.",
            },
            "keep_property": {
                "label": "Keep property",
                "consequence": "Creates ownership and reputation risk.",
            },
        }
