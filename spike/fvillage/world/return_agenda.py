"""Spoiler-safe personal re-entry summary for any human or AI mask.

A player can remember one personal next step. Shared Commons threads are
queried live and never cached into the private note, so moderation hiding
continues to work even across restarts.
"""
from __future__ import annotations

import re

MAX_NOTE = 200


def clean_note(value):
    text = str(value or "").replace("|", " ")
    text = "".join(ch if ch.isprintable() else " " for ch in text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text or len(text) > MAX_NOTE:
        return None
    return text


def reentry_lines(*, note, following):
    """Give a returning mask its own plan without caching Commons content.

    The absence greeting does not read public posts: hidden or moderated
    correspondence is fetched only by the normal agenda/Commons commands.
    """
    lines = []
    private_note = clean_note(note)
    if private_note:
        lines.append("Your saved private intention: " + private_note)
    if following:
        lines.append(
            "You follow public Commons correspondence. Use |wagenda|n "
            "to check for signed replies or closure."
        )
    if not lines:
        lines.append(
            "Use |wguide|n for something to do here, or |wagenda|n "
            "to save a next step before leaving."
        )
    else:
        lines.append("Use |wagenda|n for the current state of your plans.")
    return lines

def lamp_repair_work_lines(case, mask_id):
    """Resume only work this exact character performed on the public lamp.

    Case mutations, not a remembered quest flag, own the truth. Do not show
    another account's work to a mask that never participated.
    """
    if not isinstance(case, dict) or mask_id is None:
        return []
    changes = case.get("objective_mutations") or {}
    if not isinstance(changes, dict):
        return []
    roles = ("smith_diagnosis", "merchant_procurement", "smith_repair")
    own = {
        role: isinstance(changes.get(role), dict)
        and changes[role].get("mask_id") == mask_id
        for role in roles
    }
    if not any(own.values()):
        return []

    if case.get("state") == "aftermath":
        if case.get("branch") == "repaired":
            return [
                "Broken Mantle: the north-square gas lamp is repaired. "
                "Your contribution is recorded; no repeat repair is needed."
            ]
        return [
            "Broken Mantle: the repair window closed and the lamp remains dark. "
            "Your contribution is recorded, but this case can no longer be finished."
        ]
    if own["smith_diagnosis"]:
        if changes.get("merchant_procurement"):
            return [
                "Broken Mantle: the Merchant has procured the replacement collar. "
                "Return to the Village Square and use "
                "|wrepair finish north-square gas lamp|n."
            ]
        return [
            "Broken Mantle: your Smith diagnosis is recorded. "
            "A Merchant must procure a brass mantle collar at the Lamp Shop "
            "before you can finish the repair."
        ]
    if own["merchant_procurement"]:
        return [
            "Broken Mantle: your Merchant procurement is recorded. "
            "A Smith must install the collar at the Village Square using "
            "|wrepair finish north-square gas lamp|n."
        ]
    return []


def summary(*, note, followed, day, location, work_lines=None):
    lines = [
        "|wYour next visit|n",
        f"Village day {int(day)}. Currently at {str(location)[:90]}.",
        "Your private reminder: " + (clean_note(note) or "none yet."),
    ]
    if work_lines:
        lines.append("|wYour current village work:|n")
        lines.extend(str(line) for line in work_lines)
    if not followed:
        lines += [
            "No Commons correspondence is followed by this mask.",
            "From the Square or Tavern, use |wcommons|n to find a public "
            "thread, then |wcommons follow <number>|n to watch it.",
        ]
    else:
        lines.append("|wYour followed public correspondence:|n")
        for item in followed[:12]:
            number = int(item["id"])
            if not item.get("available"):
                # Hidden or deleted correspondence must never leak via cache.
                lines.append(
                    f"Commons #{number}: no longer publicly available. "
                    f"Use |wcommons unfollow {number}|n to clear it."
                )
                continue
            changes = []
            count = int(item.get("new_replies") or 0)
            if count:
                changes.append(f"{count} unread signed repl"
                               + ("y" if count == 1 else "ies"))
            if item.get("new_closure"):
                changes.append("new closing account")
            activity = ", ".join(changes) if changes else "no unread changes"
            lines.append(
                f"Commons #{number} [{item.get('status') or 'open'}]: "
                f"{activity}. Use |wcommons check {number}|n."
            )
    lines += [
        "Use |wagenda note = <your next step>|n to remember an intention "
        "for this mask, or |wagenda clear|n to remove it.",
        "Use |wguide|n for an immediate local lead, |wjournal|n for "
        "situations you witnessed, and |wcalendar|n for public events.",
    ]
    return "\n".join(lines)
