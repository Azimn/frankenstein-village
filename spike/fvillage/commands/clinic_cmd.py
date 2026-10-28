"""Healer clinic work at St. Lazarus, with actual treatment supplies."""
from evennia import Command


class CmdClinic(Command):
    """Examine the current visiting patient and provide physical care.

    Usage:
        clinic
        clinic assess
        clinic prepare
        clinic treat rest
        clinic treat compress
        clinic treat supported     (only with a certified cot)
        clinic brace               (Smith, real Workshop hinge)
        clinic certify             (Healer, signed patient assessment)
        clinic request records
        clinic records

    A fresh prepared dressing can be carried or handed to a different
    Healer. Only actual signed treatment changes the clinic's public record.
    """

    key = "clinic"
    aliases = ["infirmary"]
    help_category = "Village"

    def func(self):
        from world import clinic_work
        raw = (self.args or "").strip().lower().split()
        if raw in ([], ["status"], ["help"]):
            self.caller.msg(clinic_work.status(self.caller))
            return
        if raw in (["brace"], ["certify"]):
            from world import clinic_cot_work
            if raw == ["brace"]:
                result, error = clinic_cot_work.brace(self.caller)
            else:
                result, error = clinic_cot_work.certify(self.caller)
            if error:
                self.caller.msg(error)
            else:
                self.caller.msg(
                    ("You physically brace the original cot rail" if raw == ["brace"]
                     else "You clinically approve the braced cot rail")
                    + f" (signed world event {result['event_id']})."
                )
            return
        if raw == ["records"]:
            self.caller.msg(clinic_work.confidential_records(self.caller))
            return
        if raw == ["request", "records"]:
            result, error = clinic_work.act(self.caller, "request_records")
        elif raw in (["assess"], ["prepare"]):
            result, error = clinic_work.act(self.caller, raw[0])
        elif len(raw) == 2 and raw[0] == "treat":
            result, error = clinic_work.act(self.caller, "treat", raw[1])
        else:
            self.caller.msg(
                "Use clinic | clinic assess | clinic prepare | "
                "clinic treat rest|compress|supported | clinic brace | clinic certify | "
                "clinic request records | clinic records."
            )
            return
        if error:
            self.caller.msg(error)
            return
        action = result["action"]
        if action == "request_records":
            self.caller.msg(
                f"The visiting patient grants this examining Healer "
                f"permission to consult today's private case notes "
                f"(signed event {result['event_id']}). Use clinic records."
            )
        elif action == "assess":
            self.caller.msg(
                f"You assess the visiting patient and document a "
                f"{result['condition']} complaint (signed world event "
                f"{result['event_id']}). A Healer may now provide care."
            )
        elif action == "prepare":
            self.caller.msg(
                f"You prepare and carry one real linen compress "
                f"(signed world event {result['event_id']}). "
                f"It can be given to another player or used at the clinic."
            )
        else:
            self.caller.msg(
                f"You carry out {result['method']} treatment for the "
                f"{result['condition']} complaint. The clinical outcome "
                f"is signed as world event {result['event_id']}."
            )
        # Consent is private: neither the patient's details nor a consent
        # notification should be broadcast to other people in the room.
        if action != "request_records":
            self.caller.location.msg_contents(
                f"{self.caller.key} performs a real clinic {action} action.",
                exclude=[self.caller],
            )
