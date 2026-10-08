"""A shared place to ask, offer, answer, and remember village affairs."""

from evennia import Command

from world import commons, commons_state


READ_ROOMS = frozenset({"Village Square", "The Blood of the Vine"})
POST_ROOM = "Village Square"


class CmdCommons(Command):
    """Use the village's public correspondence board.

    Usage:
        commons
        commons archive
        commons <number>
        commons post need|offer|gathering|notice = <words>
        commons reply <number> = <words>
        commons close <number> = <closing account>
        commons report <number> = <reason>
        commons hide <number> = <reason>  (human staff)

    The board is not a quest list. Notes remain public and may be answered
    by other travelers on other days. Closing is the author's own account,
    not an automatic reward or a universal declaration of fact.
    """

    key = "commons"
    aliases = ["noticeboard", "notices"]
    help_category = "Village"

    def _location_ok(self):
        room = self.caller.location
        if room and room.key in READ_ROOMS and room.tags.has("ic", category="side"):
            return True
        if room and room.tags.has("ooc", category="side"):
            self.caller.msg("The public commons is in character. Cross the front door.")
        else:
            self.caller.msg(
                "The noticeboard is in the Village Square. Bram keeps "
                "a copy at the Blood of the Vine."
            )
        return False

    def _detail(self, notice_id):
        entry = commons_state.get_notice(commons.current(), notice_id)
        if not entry or entry.get("hidden"):
            self.caller.msg("No public notice has that number.")
            return
        lines = [
            f"|wCommons #{entry['id']}|n [{entry['kind']}, {entry['status']}]",
            f"From {entry['author']['mask']}, village day {entry['day']}:",
            entry["body"],
        ]
        if entry["replies"]:
            lines.append("Signed correspondence:")
            for reply in entry["replies"]:
                lines.append(
                    f"  {reply['by']['mask']} (day {reply['day']}): {reply['body']}"
                )
        else:
            lines.append("No one has written a response yet.")
        if entry["resolution"]:
            lines.append(
                "Closing account by " + entry["resolution"]["by"]["mask"]
                + ": " + entry["resolution"]["body"]
            )
        if entry["status"] == "open":
            lines.append(
                f"Reply: commons reply {notice_id} = <words> "
                f"(you need not be the author)."
            )
        lines.append(f"Report abuse: commons report {notice_id} = <reason>.")
        self.caller.msg("\n".join(lines))

    def _index(self, archive=False):
        entries = commons_state.notices(
            commons.current(), include_closed=True
        )
        entries = [
            entry for entry in entries
            if (entry["status"] == "closed") == archive
        ][:12]
        heading = "|wVillage Commons: " + (
            "past correspondence" if archive else "open correspondence"
        ) + "|n"
        lines = [heading]
        for entry in entries:
            lines.append(
                f"#{entry['id']} [{entry['kind']}] "
                f"{entry['author']['mask']}: {entry['body'][:100]} "
                f"({len(entry['replies'])} replies)"
            )
        if not entries:
            lines.append("No entries in this part of the commons.")
        lines.append(
            "Read: commons <number> | Past: commons archive | "
            "Post from the square: commons post need = <words>"
        )
        self.caller.msg("\n".join(lines))

    def func(self):
        if not self._location_ok():
            return
        raw = (self.args or "").strip()
        if not raw:
            self._index()
            return
        if raw.lower() == "archive":
            self._index(archive=True)
            return
        if raw.isdecimal():
            self._detail(int(raw))
            return

        head, has_equal, message = raw.partition("=")
        words = head.strip().split()
        if not has_equal or len(words) < 2:
            self.caller.msg(
                "Use commons post need|offer|gathering|notice = <words>, "
                "commons reply <number> = <words>, or commons <number>."
            )
            return

        action = words[0].lower()
        text = message.strip()
        if action == "post":
            if self.caller.location.key != POST_ROOM:
                self.caller.msg(
                    "Original notices are posted at the Village Square board."
                )
                return
            if len(words) != 2:
                self.caller.msg(
                    "Use commons post need|offer|gathering|notice = <words>."
                )
                return
            record, error = commons.change(
                self.caller, "post", kind=words[1], text=text
            )
            if not error:
                self.caller.msg(
                    f"Commons #{record['id']} posted. Other travelers can "
                    "answer even after you log out."
                )
                self.caller.location.msg_contents(
                    f"{self.caller.key} pins a note to the village board.",
                    exclude=[self.caller],
                )
        elif action in {"reply", "close", "report", "hide"}:
            if len(words) != 2 or not words[1].isdecimal():
                self.caller.msg(f"Use commons {action} <number> = <words>.")
                return
            number = int(words[1])
            if action == "report":
                record, error = commons.report(self.caller, number, text)
                if not error:
                    self.caller.msg(
                        f"Report #{record['id']} sent for human review. "
                        "The notice has not been automatically removed."
                    )
            else:
                record, error = commons.change(
                    self.caller, action, notice_id=number, text=text
                )
                if not error:
                    self.caller.msg(
                        f"Commons #{number} " + {
                            "reply": "received your signed response.",
                            "close": "closed with your account of the outcome.",
                            "hide": "hidden from public view by staff.",
                        }[action]
                    )
        else:
            self.caller.msg("Unknown commons action. Use help commons.")
            return
        if error:
            self.caller.msg(error)
