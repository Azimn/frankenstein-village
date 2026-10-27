"""Pure EDGE-15 bridge casework, without a second authoritative state store.

The public mystery registry owns the persisted case. The world event ledger
owns source identity. Neither a Detective nor a Chronicler can certify a
culprit or a metaphysical explanation.
"""
import copy

MAX_CASE_RECORDS = 30


def _id(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _time(day, hour):
    return _id(day) and type(hour) is int and 0 <= hour <= 23


def _actor(account_id, mask_id, mask, event_id):
    return _id(account_id) and _id(mask_id) and _id(event_id) and bool(str(mask or "").strip())


def examine(state, *, day, hour, account_id, mask_id, mask, event_id, observation):
    """Sign one daily firsthand physical examination, never a conclusion."""
    result = copy.deepcopy(state or {})
    if not _time(day, hour) or not _actor(account_id, mask_id, mask, event_id):
        return result, False, "Invalid signed examination identity or village time."
    if not isinstance(observation, dict) or observation.get("day") != day:
        return result, False, "Inspect the actual bridge plaque today first."
    if not _id(observation.get("source_event_id")):
        return result, False, "The physical observation lacks a signed ledger source."
    if observation.get("pattern") not in {"daylight", "lamplight", "rainwater"}:
        return result, False, "The physical observation has no recognized pattern."
    if not any(
        isinstance(w, dict) and w.get("account_id") == account_id
        and w.get("mask_id") == mask_id
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
    exams = [x for x in result.get("case_examinations") or [] if x.get("day") == day]
    if len(exams) != 1:
        return result, False, "A signed Detective examination is required today."
    exam = exams[0]
    if any(x.get("day") == day for x in result.get("case_bulletins") or []):
        return result, False, "A public case bulletin is already signed today."
    if account_id == exam.get("account_id"):
        return result, False, "An independent account must publish the Detective's findings."
    if not isinstance(source, dict) or source.get("status") != "complete":
        return result, False, "The Detective source event is not complete."
    if source.get("kind") != "village.bridge_plaque_examined" or source.get("id") != exam.get("event_id"):
        return result, False, "The Detective source event does not match this case."
    actor = source.get("actor") or {}
    payload = source.get("payload") or {}
    consequence = source.get("consequence") or {}
    if (
        actor.get("account_id") != exam.get("account_id")
        or actor.get("mask_id") != exam.get("mask_id")
        or actor.get("mask") != exam.get("mask")
        or payload.get("professional_calling") != "detective"
        or payload.get("location") != "The Old Stone Bridge"
        or payload.get("day") != day
        or payload.get("hour") != exam.get("hour")
        or payload.get("observation_event_id") != exam.get("observation_event_id")
        or consequence.get("case_exam_event_id") != exam.get("event_id")
        or consequence.get("observation_event_id") != exam.get("observation_event_id")
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


def case_lines(state, day):
    state = state or {}
    exams = list(state.get("case_examinations") or [])
    bulletins = list(state.get("case_bulletins") or [])
    lines = [
        "Bridge plaque case desk: the missing plaque is an open question.",
        "Detective: inspect the original plaque on the Old Stone Bridge, then mystery bridge examine.",
        "Chronicler: at Village Square, use mystery bridge publish after an independent signed examination.",
    ]
    for exam in exams[-3:]:
        lines.append(
            f"Day {exam['day']} Detective {exam['mask']} examination event "
            f"{exam['event_id']}, physical observation {exam['observation_event_id']}."
        )
    for bulletin in bulletins[-3:]:
        lines.append(
            f"Day {bulletin['day']} Chronicler {bulletin['mask']} bulletin event "
            f"{bulletin['event_id']}, Detective source {bulletin['source_event_id']}."
        )
    if not any(b.get("day") == day for b in bulletins):
        lines.append("No independently published case bulletin for this village day.")
    lines.append("Physical marks and testimony do not identify a culprit.")
    return lines
