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
        clinic request records
        clinic records
        clinic procure  (Merchant at Market Lane)
        clinic receive  (Healer at St. Lazarus)
        clinic investigate illness  (Detective: unrelated illness interpretation)
        clinic investigate exposure  (Detective: possible exposure interpretation)

    The Detective must first look at the cot and bring a real cluster of
    mushrooms from the village well. Competing explanations remain unproven.

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
        if raw == ["procure"]:
            result, error = clinic_work.procure(self.caller)
            self.caller.msg(error or (
                f"You withdraw a real sealed clinic linen parcel from finite "
                f"market stock (signed Merchant event {result['event_id']}). "
                "Carry it to St. Lazarus for a separate Healer to accept."
            ))
            return
        if raw == ["receive"]:
            result, error = clinic_work.receive(self.caller)
            self.caller.msg(error or (
                f"You inspect and accept two clean linen dressings into the "
                f"shared clinic cabinet (signed Healer event {result['event_id']}, "
                f"Merchant source event {result['source_event_id']})."
            ))
            return
        if raw in (["investigate"], ["investigate", "illness"],
                   ["investigate", "exposure"]):
            from world.clinic_inquiry_work import investigate
            interpretation = ("possible_exposure" if raw[-1] == "exposure"
                              else "unrelated_illness")
            result, error = investigate(self.caller, interpretation)
            if error:
                self.caller.msg(error)
            else:
                self.caller.msg(
                    f"You sign an independent procedural clinic inquiry "
                    f"(world event {result['event_id']}, verified Healer source "
                    f"{result['source_event_id']}). The original cot records "
                    f"the physical specimen {result['case_item_id']} and two "
                    "competing explanations ({result['interpretation']} versus "
                    f"{result['alternative']}). Neither cause is proven; "
                    "private case notes remain confidential."
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
                "clinic treat rest or clinic treat compress | clinic request records | clinic records | clinic procure | clinic receive | clinic investigate illness|exposure. "
                "Bring a real well-mushroom specimen and look at the clinic cot first."
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
