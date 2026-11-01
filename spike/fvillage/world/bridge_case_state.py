"""Pure EDGE-15 bridge casework, without a second authoritative state store.

The public mystery registry owns the persisted case. The world event ledger
owns source identity. Neither a Detective nor a Chronicler can certify a
culprit or a metaphysical explanation.
"""
import copy
from collections.abc import Mapping

MAX_CASE_RECORDS = 30


def _id(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _time(day, hour):
    return _id(day) and type(hour) is int and 0 <= hour <= 23


def _actor(account_id, mask_id, mask, event_id):
    return _id(account_id) and _id(mask_id) and _id(event_id) and isinstance(mask, str) and bool(mask.strip())


def examine(state, *, day, hour, account_id, mask_id, mask, event_id, observation):
    """Sign one daily firsthand physical examination, never a conclusion."""
    result = copy.deepcopy(state or {})
    if not _time(day, hour) or not _actor(account_id, mask_id, mask, event_id):
        return result, False, "Invalid signed examination identity or village time."
    if (not isinstance(observation, Mapping)
            or type(observation.get("day")) is not int
            or observation["day"] != day):
        return result, False, "Inspect the actual bridge plaque today first."
    if (not _id(observation.get("source_event_id"))
            or observation["source_event_id"] == event_id):
        return result, False, "The physical observation lacks a signed ledger source."
    if observation.get("pattern") not in {"daylight", "lamplight", "rainwater"}:
        return result, False, "The physical observation has no recognized pattern."
    if not any(
        isinstance(w, Mapping) and _id(w.get("account_id"))
        and _id(w.get("mask_id")) and w["account_id"] == account_id
        and w["mask_id"] == mask_id
        for w in (observation.get("witnesses") or [])
    ):
        return result, False, "You must personally witness the physical plaque."
    if any(x.get("day") == day for x in result.get("case_examinations") or []):
        return result, False, "A Detective examination is already signed today."
    record = {
        "event_id": event_id, "observation_event_id": observation["source_event_id"],
        "day": day, "hour": hour, "account_id": account_id,
        "mask_id": mask_id, "mask": mask, "pattern": observation["pattern"],
        "finding": "physical_marks_only",
    }
    result["case_examinations"] = (
        list(result.get("case_examinations") or []) + [record]
    )[-MAX_CASE_RECORDS:]
    return result, True, None


def publish(state, *, day, hour, account_id, mask_id, mask, event_id, source):
    """Publish an attributed source-limited bulletin from an independent account."""
    result = copy.deepcopy(state or {})
    if not _time(day, hour) or not _actor(account_id, mask_id, mask, event_id):
        return result, False, "Invalid bulletin identity or village time."
    exams = [x for x in result.get("case_examinations") or []
             if isinstance(x, Mapping) and type(x.get("day")) is int
             and x["day"] == day]
    if len(exams) != 1:
        return result, False, "A signed Detective examination is required today."
    exam = exams[0]
    if any(x.get("day") == day for x in result.get("case_bulletins") or []):
        return result, False, "A public case bulletin is already signed today."
    if (not _actor(exam.get("account_id"), exam.get("mask_id"),
                   exam.get("mask"), exam.get("event_id"))
            or not _id(exam.get("observation_event_id"))
            or exam["event_id"] == exam["observation_event_id"]
            or not _time(exam.get("day"), exam.get("hour"))
            or exam["hour"] > hour
            or event_id in {exam["event_id"], exam["observation_event_id"]}):
        return result, False, "The persisted examination source is malformed or out of order."
    if account_id == exam.get("account_id"):
        return result, False, "An independent account must publish the Detective's findings."
    if not isinstance(source, Mapping) or source.get("status") != "complete":
        return result, False, "The Detective source event is not complete."
    if (source.get("kind") != "village.bridge_plaque_examined"
            or not _id(source.get("id")) or source["id"] != exam["event_id"]):
        return result, False, "The Detective source event does not match this case."
    actor = source.get("actor") or {}
    payload = source.get("payload") or {}
    consequence = source.get("consequence") or {}
    if (
        not _id(actor.get("account_id"))
        or actor["account_id"] != exam["account_id"]
        or not _id(actor.get("mask_id"))
        or actor["mask_id"] != exam["mask_id"]
        or actor.get("mask") != exam.get("mask")
        or payload.get("professional_calling") != "detective"
        or payload.get("location") != "The Old Stone Bridge"
        or payload.get("day") != day
        or payload.get("hour") != exam.get("hour")
        or not _id(payload.get("observation_event_id"))
        or payload["observation_event_id"] != exam["observation_event_id"]
        or not _id(consequence.get("case_exam_event_id"))
        or consequence["case_exam_event_id"] != exam["event_id"]
        or not _id(consequence.get("observation_event_id"))
        or consequence["observation_event_id"] != exam["observation_event_id"]
        or consequence.get("pattern") != exam.get("pattern")
        or consequence.get("finding") != "physical_marks_only"
    ):
        return result, False, "The signed source does not substantiate this examination."
    if not _time(payload.get("day"), payload.get("hour")) or hour < exam["hour"]:
        return result, False, "A bulletin cannot precede the source examination."
    bulletin = {
        "event_id": event_id, "source_event_id": exam["event_id"],
        "observation_event_id": exam["observation_event_id"],
        "day": day, "hour": hour, "account_id": account_id,
        "mask_id": mask_id, "mask": mask,
        "source_account_id": exam["account_id"], "pattern": exam["pattern"],
        "status": "attributed_evidence_only",
    }
    result["case_bulletins"] = (
        list(result.get("case_bulletins") or []) + [bulletin]
    )[-MAX_CASE_RECORDS:]
    return result, True, None



def _signed_exam(state, exam, get_event):
    """Verify an original physical observation and completed Detective act."""
    if not isinstance(exam, Mapping) or not callable(get_event):
        return False
    if (not _actor(exam.get("account_id"), exam.get("mask_id"),
                   exam.get("mask"), exam.get("event_id"))
            or not _time(exam.get("day"), exam.get("hour"))
            or not _id(exam.get("observation_event_id"))
            or exam["event_id"] == exam["observation_event_id"]
            or exam.get("finding") != "physical_marks_only"
            or exam.get("pattern") not in {"daylight", "lamplight", "rainwater"}):
        return False
    event = get_event(exam["event_id"])
    observation = get_event(exam["observation_event_id"])
    if not isinstance(event, Mapping) or not isinstance(observation, Mapping):
        return False
    actor, payload, consequence = (event.get("actor"), event.get("payload"),
                                    event.get("consequence"))
    witness, observed = observation.get("actor"), observation.get("payload")
    if not all(isinstance(v, Mapping) for v in (
            actor, payload, consequence, witness, observed)):
        return False
    if not (
        event.get("status") == "complete"
        and event.get("kind") == "village.bridge_plaque_examined"
        and type(event.get("id")) is int and event["id"] == exam["event_id"]
        and actor.get("account_id") == exam["account_id"]
        and type(actor.get("account_id")) is int
        and actor.get("mask_id") == exam["mask_id"]
        and type(actor.get("mask_id")) is int
        and actor.get("mask") == exam["mask"]
        and payload.get("professional_calling") == "detective"
        and payload.get("location") == "The Old Stone Bridge"
        and type(payload.get("day")) is int and payload["day"] == exam["day"]
        and type(payload.get("hour")) is int and payload["hour"] == exam["hour"]
        and type(payload.get("observation_event_id")) is int
        and payload["observation_event_id"] == exam["observation_event_id"]
        and type(consequence.get("case_exam_event_id")) is int
        and consequence["case_exam_event_id"] == exam["event_id"]
        and type(consequence.get("observation_event_id")) is int
        and consequence["observation_event_id"] == exam["observation_event_id"]
        and consequence.get("pattern") == exam["pattern"]
        and consequence.get("finding") == "physical_marks_only"
        and observation.get("status") == "complete"
        and observation.get("kind") == "public_mystery.bridge_plaque.observed"
        and type(observation.get("id")) is int
        and observation["id"] == exam["observation_event_id"]
        and type(witness.get("account_id")) is int
        and witness["account_id"] == exam["account_id"]
        and type(witness.get("mask_id")) is int
        and witness["mask_id"] == exam["mask_id"]
        and witness.get("mask") == exam["mask"]
        and observed.get("public_mystery_id") == "PUBLIC-BRIDGE-PLAQUE"
        and type(observed.get("day")) is int and observed["day"] == exam["day"]
        and type(observed.get("hour")) is int
        and 0 <= observed["hour"] <= exam["hour"]
        and observed.get("pattern") == exam["pattern"]
        and isinstance(observed.get("weather"), str)
        and bool(observed["weather"])
    ):
        return False
    # The original physical witness is stored on the canonical bridge record.
    # A borrowed event ID or a different person's testimony is not evidence.
    for row in state.get("observations") or []:
        if not isinstance(row, Mapping):
            continue
        if (type(row.get("day")) is not int or row["day"] != exam["day"]
                or type(row.get("hour")) is not int
                or row["hour"] != observed["hour"]
                or row.get("weather") != observed["weather"]
                or row.get("pattern") != exam["pattern"]):
            continue
        for item in row.get("witnesses") or []:
            if (isinstance(item, Mapping)
                    and type(item.get("source_event_id")) is int
                    and item["source_event_id"] == exam["observation_event_id"]
                    and type(item.get("account_id")) is int
                    and item["account_id"] == exam["account_id"]
                    and type(item.get("mask_id")) is int
                    and item["mask_id"] == exam["mask_id"]
                    and item.get("mask") == exam["mask"]):
                signed_consequence = observation.get("consequence")
                return (signed_consequence is None
                        or (isinstance(signed_consequence, Mapping)
                            and signed_consequence.get("source_event_id")
                            == observation["id"]
                            and signed_consequence.get("pattern") == exam["pattern"]))
    return False


def _signed_bulletin(state, bulletin, get_event):
    if not isinstance(bulletin, Mapping) or not callable(get_event):
        return False
    if (not _actor(bulletin.get("account_id"), bulletin.get("mask_id"),
                   bulletin.get("mask"), bulletin.get("event_id"))
            or not _time(bulletin.get("day"), bulletin.get("hour"))
            or not _id(bulletin.get("source_event_id"))
            or not _id(bulletin.get("observation_event_id"))
            or not _id(bulletin.get("source_account_id"))
            or bulletin.get("status") != "attributed_evidence_only"):
        return False
    exams = [x for x in state.get("case_examinations") or []
             if isinstance(x, Mapping)
             and x.get("event_id") == bulletin["source_event_id"]]
    if len(exams) != 1:
        return False
    exam = exams[0]
    if (not _signed_exam(state, exam, get_event)
            or bulletin["source_account_id"] != exam["account_id"]
            or bulletin["account_id"] == exam["account_id"]
            or bulletin["observation_event_id"] != exam["observation_event_id"]
            or bulletin.get("pattern") != exam["pattern"]
            or bulletin["day"] != exam["day"]
            or bulletin["hour"] < exam["hour"]
            or bulletin["event_id"] in {
                exam["event_id"], exam["observation_event_id"]}):
        return False
    event = get_event(bulletin["event_id"])
    if not isinstance(event, Mapping):
        return False
    actor, payload, consequence = (event.get("actor"), event.get("payload"),
                                    event.get("consequence"))
    if not all(isinstance(v, Mapping) for v in (actor, payload, consequence)):
        return False
    return (
        event.get("status") == "complete"
        and event.get("kind") == "village.bridge_case_bulletin"
        and type(event.get("id")) is int and event["id"] == bulletin["event_id"]
        and type(actor.get("account_id")) is int
        and actor["account_id"] == bulletin["account_id"]
        and type(actor.get("mask_id")) is int
        and actor["mask_id"] == bulletin["mask_id"]
        and actor.get("mask") == bulletin["mask"]
        and payload.get("professional_calling") == "chronicler"
        and payload.get("location") == "Village Square"
        and type(payload.get("day")) is int
        and payload["day"] == bulletin["day"]
        and type(payload.get("hour")) is int
        and payload["hour"] == bulletin["hour"]
        and type(payload.get("source_event_id")) is int
        and payload["source_event_id"] == bulletin["source_event_id"]
        and type(consequence.get("case_bulletin_event_id")) is int
        and consequence["case_bulletin_event_id"] == bulletin["event_id"]
        and type(consequence.get("source_event_id")) is int
        and consequence["source_event_id"] == bulletin["source_event_id"]
        and type(consequence.get("observation_event_id")) is int
        and consequence["observation_event_id"] == bulletin["observation_event_id"]
        and consequence.get("status") == "attributed_evidence_only"
    )


def case_lines(state, day, *, get_event=None):
    """Never project persisted IDs as signed public facts without ledger proof."""
    state = state if isinstance(state, Mapping) else {}
    exams = list(state.get("case_examinations") or [])
    bulletins = list(state.get("case_bulletins") or [])
    lines = [
        "Bridge plaque case desk: the missing plaque is an open question.",
        "Detective: inspect the original plaque on the Old Stone Bridge, then mystery bridge examine.",
        "Chronicler: at Village Square, use mystery bridge publish after an independent signed examination.",
    ]
    for exam in exams[-3:]:
        if _signed_exam(state, exam, get_event):
            lines.append(
                f"Day {exam['day']} Detective {exam['mask']} examination event "
                f"{exam['event_id']}, physical observation {exam['observation_event_id']}."
            )
        else:
            lines.append("A stored bridge examination is unverified; no signed claim is displayed.")
    verified_today = False
    for bulletin in bulletins[-3:]:
        if _signed_bulletin(state, bulletin, get_event):
            lines.append(
                f"Day {bulletin['day']} Chronicler {bulletin['mask']} bulletin event "
                f"{bulletin['event_id']}, Detective source {bulletin['source_event_id']}."
            )
            if bulletin["day"] == day:
                verified_today = True
        else:
            lines.append("A stored bridge bulletin is unverified; no signed publication is displayed.")
    if not verified_today:
        lines.append("No independently published case bulletin for this village day.")
    lines.append("Physical marks and testimony do not identify a culprit.")
    return lines
