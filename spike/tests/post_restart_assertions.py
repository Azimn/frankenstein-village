"""Assertions run after the player telnet pass and a real server restart."""

from evennia.utils import search

from world.residents import facts_known_by_player, resident_state


def one(key):
    found = [obj for obj in search.search_object(key) if obj.key == key]
    assert len(found) == 1, (key, len(found))
    return found[0]


silas = one("Silas Crowe")
smoke = one("SmokeTester")
state = resident_state(silas)
relation = (state.get("relationships") or {}).get(str(smoke.id))
assert relation, "telnet interactions did not persist a Silas relationship"
assert relation["familiarity"] >= 8
assert state["character_depth"] in {"C", "B", "A"}
assert state["simulation_resolution"] in {"reactive", "engaged", "focused"}
assert state["facts"], "history question did not persist progressive characterization"
known = facts_known_by_player(silas, smoke)
assert known, "revealed fact was not recorded for the player mask"

population = list(search.search_tag("resident", category="system"))
assert len(population) == 36, "resident population changed across restart"

print("POST_RESTART_RESIDENT_ASSERTIONS_GREEN")
