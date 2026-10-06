"""Small systemic-object property layer.

Mechanical properties are deliberately few. The property tag says what an
object can do in the simulation; the paired value supplies the magnitude.
Flavor text remains unconstrained and is not parsed back into mechanics.

This is the first production slice of the systemic-object plan. Hidden
properties, perception gating, crafting transformations, and legend detection
remain later phases.
"""

from __future__ import annotations


MECHANIC_CATEGORY = "mechanic"

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


def _values(obj):
    """Return a plain copy of persisted mechanical magnitudes."""
    return dict(obj.db.mechanic_values or {})


def configure_mechanical_properties(obj, properties):
    """Converge one object mechanical definition without touching live state.

    properties maps canonical property names to magnitudes or payloads.
    Configuration is definition data. Mutable runtime counters, such as a
    sideboard item remaining servings, live elsewhere and are intentionally
    not reset here.
    """
    properties = dict(properties or {})
    unknown = sorted(set(properties) - MECHANICAL_PROPERTIES)
    if unknown:
        raise ValueError(
            "unknown mechanical properties: " + ", ".join(unknown)
        )

    for name in MECHANICAL_PROPERTIES:
        if obj.tags.has(name, category=MECHANIC_CATEGORY):
            obj.tags.remove(name, category=MECHANIC_CATEGORY)

    normalized = {}
    for name, value in properties.items():
        obj.tags.add(name, category=MECHANIC_CATEGORY)
        normalized[name] = value

    obj.db.mechanic_values = normalized
    return dict(normalized)


def has_mechanical_property(obj, name):
    """Return whether an object exposes a canonical mechanical property."""
    name = str(name or "").strip().lower()
    if name not in MECHANICAL_PROPERTIES:
        return False
    return bool(obj.tags.has(name, category=MECHANIC_CATEGORY))


def mechanical_value(obj, name, default=None):
    """Read one mechanical value only when its property tag is present."""
    name = str(name or "").strip().lower()
    if not has_mechanical_property(obj, name):
        return default
    return _values(obj).get(name, default)


def mechanical_properties(obj):
    """Return the object visible mechanical definition as a plain mapping."""
    values = _values(obj)
    return {
        name: values.get(name)
        for name in MECHANICAL_PROPERTIES
        if obj.tags.has(name, category=MECHANIC_CATEGORY)
    }
