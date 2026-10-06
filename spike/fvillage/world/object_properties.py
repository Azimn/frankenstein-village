"""Small systemic-object property and perception layer.

Mechanical properties are deliberately few. The property tag says what an
object can do in the simulation; the paired value supplies the magnitude.
Flavor text remains unconstrained and is not parsed back into mechanics.

Visible and hidden properties share one simulation vocabulary. Hidden
properties remain mechanically active while ordinary presentation omits them.
Per-mask knowledge is separate from object truth: learning a hidden property
records what that observer discovered without changing the object definition.
"""

from __future__ import annotations


MECHANIC_CATEGORY = "mechanic"
HIDDEN_PREFIX = "hidden:"

MECHANICAL_PROPERTIES = frozenset({
    "harm",
    "toxin",
    "mend",
    "ward",
    "holds",
    "fuel",
    "uses",
    "worth",
    "perish",
    "tale",
})

_PROPERTY_KNOWLEDGE_TEXT = {
    "harm": "You have learned that it can cause immediate harm.",
    "toxin": "You have learned that it can be toxic.",
    "mend": "You have learned that it can restore injury or illness.",
    "ward": "You have learned that it can provide protection.",
    "holds": "You have learned that it has useful carrying capacity.",
    "fuel": "You have learned that it can serve as fuel.",
    "uses": "You have learned that its useful life is finite.",
    "worth": "You have learned something reliable about its material value.",
    "perish": "You have learned that it can spoil or decay.",
    "tale": "You have learned that it carries recoverable information.",
}


def _values(obj):
    """Return a plain copy of persisted mechanical magnitudes."""
    return dict(obj.db.mechanic_values or {})


def _hidden_tag(name):
    return f"{HIDDEN_PREFIX}{name}"


def _normalize_definition(properties, hidden_properties):
    visible = dict(properties or {})
    hidden = dict(hidden_properties or {})
    unknown = sorted(
        (set(visible) | set(hidden)) - MECHANICAL_PROPERTIES
    )
    if unknown:
        raise ValueError(
            "unknown mechanical properties: " + ", ".join(unknown)
        )
    overlap = sorted(set(visible) & set(hidden))
    if overlap:
        raise ValueError(
            "mechanical properties cannot be both visible and hidden: "
            + ", ".join(overlap)
        )
    return visible, hidden


def configure_mechanical_properties(
    obj,
    properties,
    *,
    hidden_properties=None,
):
    """Converge one mechanical definition without touching mutable live state.

    properties maps player-visible canonical properties to magnitudes or
    payloads. hidden_properties uses the same vocabulary but stores those
    properties behind hidden:<name> mechanic tags.

    Visibility affects perception only. Both visible and hidden definitions
    remain authoritative simulation inputs. Mutable runtime counters, such as
    remaining servings, live elsewhere and are intentionally not reset here.
    """
    visible, hidden = _normalize_definition(properties, hidden_properties)

    for name in MECHANICAL_PROPERTIES:
        for tag in (name, _hidden_tag(name)):
            if obj.tags.has(tag, category=MECHANIC_CATEGORY):
                obj.tags.remove(tag, category=MECHANIC_CATEGORY)

    normalized = {}
    for name, value in visible.items():
        obj.tags.add(name, category=MECHANIC_CATEGORY)
        normalized[name] = value
    for name, value in hidden.items():
        obj.tags.add(_hidden_tag(name), category=MECHANIC_CATEGORY)
        normalized[name] = value

    obj.db.mechanic_values = normalized
    return dict(normalized)


def has_mechanical_property(obj, name):
    """Return whether a canonical property is openly exposed on the object."""
    name = str(name or "").strip().lower()
    if name not in MECHANICAL_PROPERTIES:
        return False
    return bool(obj.tags.has(name, category=MECHANIC_CATEGORY))


def is_hidden_mechanical_property(obj, name):
    """Return whether a canonical property is mechanically real but hidden."""
    name = str(name or "").strip().lower()
    if name not in MECHANICAL_PROPERTIES:
        return False
    return bool(
        obj.tags.has(_hidden_tag(name), category=MECHANIC_CATEGORY)
    )


def mechanical_value(obj, name, default=None):
    """Read a simulation value regardless of whether perception hides it."""
    name = str(name or "").strip().lower()
    if name not in MECHANICAL_PROPERTIES:
        return default
    if not (
        has_mechanical_property(obj, name)
        or is_hidden_mechanical_property(obj, name)
    ):
        return default
    return _values(obj).get(name, default)


def mechanical_properties(obj):
    """Return only the object's openly exposed mechanical definition."""
    values = _values(obj)
    return {
        name: values.get(name)
        for name in MECHANICAL_PROPERTIES
        if obj.tags.has(name, category=MECHANIC_CATEGORY)
    }


def hidden_mechanical_properties(obj):
    """Return hidden simulation truth for trusted engine/test callers only."""
    values = _values(obj)
    return {
        name: values.get(name)
        for name in MECHANICAL_PROPERTIES
        if obj.tags.has(_hidden_tag(name), category=MECHANIC_CATEGORY)
    }


def effective_mechanical_properties(obj):
    """Return complete simulation truth, independent of perception."""
    result = hidden_mechanical_properties(obj)
    result.update(mechanical_properties(obj))
    return result


def _observer_knowledge(observer):
    try:
        return dict(observer.db.object_property_knowledge or {})
    except Exception:
        return {}


def hidden_property_knowledge(observer, obj):
    """Return what one observer remembers learning about this exact object."""
    if observer is None or obj is None:
        return {}
    records = _observer_knowledge(observer).get(str(obj.id)) or {}
    return {
        str(name): dict(record)
        for name, record in dict(records).items()
    }


def learn_hidden_property(observer, obj, name, *, source):
    """Persist one observer's discovery without modifying object truth.

    The stored magnitude is what the observer learned at discovery time. That
    distinction is intentional: later object transformations must not rewrite a
    character's memory retroactively.
    """
    name = str(name or "").strip().lower()
    if not is_hidden_mechanical_property(obj, name):
        return None, False

    knowledge = _observer_knowledge(observer)
    object_key = str(obj.id)
    object_records = {
        str(key): dict(value)
        for key, value in dict(knowledge.get(object_key) or {}).items()
    }
    if name in object_records:
        return dict(object_records[name]), False

    record = {
        "property": name,
        "value": mechanical_value(obj, name),
        "source": str(source or "discovery"),
        "object_id": obj.id,
        "object_key": obj.key,
    }
    object_records[name] = record
    knowledge[object_key] = object_records
    observer.db.object_property_knowledge = knowledge
    return dict(record), True


def perception_notes(observer, obj):
    """Render only hidden-property knowledge this observer has actually earned."""
    notes = []
    for name, record in sorted(hidden_property_knowledge(observer, obj).items()):
        statement = _PROPERTY_KNOWLEDGE_TEXT.get(
            name,
            f"You have learned that it carries the hidden property {name}.",
        )
        source = str(record.get("source") or "discovery").replace("_", " ")
        notes.append(f"{statement} (learned by {source})")
    return notes
