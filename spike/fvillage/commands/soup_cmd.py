"""Shared physical tavern food work, preserving ordinary player verbs."""
from evennia import Command


class CmdSoup(Command):
    """Develop a real soup recipe and supply a shared village kitchen.

    Usage:
        soup
        soup prep <turnip|barley> <thyme|salt|pepper>
        soup simmer
        soup notebook
        soup procure             (Merchant, Market Lane)
        soup deliver             (any courier carrying the real crate)
        soup refuge <hound mask>  (Innkeep, Hound present with signed dispatch)

    The kitchen has finite pantry supplies, a renewing daily baseline,
    a permanent work log and individual recipe notebooks. Prepared packets
    and finished bowls are actual giveable objects. Use 'eat homemade soup'
    to taste a bowl through the game's normal eating and hunger rules.
    """

    key = "soup"
    aliases = ["cookery"]
    help_category = "Village"

    def func(self):
        from world import soup_kitchen
        caller = self.caller
        loc = getattr(caller, "location", None)
        if not loc or not loc.tags.has("ic", category="side"):
            caller.msg("Village kitchen work is in-character. Use the front door.")
            return
        raw = (self.args or "").strip().lower()
        if raw in ("", "stock", "status"):
            caller.msg(soup_kitchen.status(caller))
            return
        if raw.startswith("refuge"):
            from world import refuge_work
            name = raw[len("refuge"):].strip()
            result, error = refuge_work.serve(caller, name)
            if error:
                caller.msg(error)
                return
            caller.msg(
                f"You serve one real bowl of refuge soup to the Hound "
                f"(signed event {result['event_id']}); the dispatch is consumed. "
                f"{result['turnip']} turnip portions remain in the Tavern pantry."
            )
            caller.location.msg_contents(
                f"{caller.key} serves a witnessed traveler from the finite pantry.",
                exclude=[caller])
            return
        if raw == "notebook":
            caller.msg(soup_kitchen.recipe_notes(caller))
            return
        if raw.startswith("prep "):
            parts = raw.split()
            if len(parts) != 3:
                caller.msg("Choose: soup prep turnip thyme, or barley salt, etc.")
                return
            result, error = soup_kitchen.prep(caller, parts[1], parts[2])
            if error:
                caller.msg(error)
                return
            caller.msg(
                f"You measure real {result['base']} and {result['seasoning']} "
                f"into a packet (world event {result['event_id']}). "
                "The shared pantry stock decreases. Give the packet away "
                "or finish it with soup simmer."
            )
            caller.location.msg_contents(
                f"{caller.key} measures ingredients from the communal kitchen.",
                exclude=[caller])
            return
        if raw == "simmer":
            result, error = soup_kitchen.simmer(caller)
            if error:
                caller.msg(error)
                return
            caller.msg(
                f"You simmer your {result['base']} and {result['seasoning']} "
                f"soup into a real, shareable bowl. Quality {result['quality']}. "
                f"World event {result['event_id']}. "
                "Taste with eat homemade soup, or hand the serving to someone. "
                "The recipe is remembered in soup notebook."
            )
            caller.location.msg_contents(
                f"{caller.key} finishes a fresh bowl of homemade soup.",
                exclude=[caller])
            return
        if raw == "procure":
            result, error = soup_kitchen.procure(caller)
            if error:
                caller.msg(error)
                return
            caller.msg(
                "You collect a physical crate of kitchen roots. "
                f"{result['remaining']} market crates remain today. "
                "Carry it to the Blood of the Vine and use soup deliver, "
                "or give it to a courier."
            )
            caller.location.msg_contents(
                f"{caller.key} loads a crate for the village kitchen.",
                exclude=[caller])
            return
        if raw == "deliver":
            result, error = soup_kitchen.deliver(caller)
            if error:
                caller.msg(error)
                return
            caller.msg(
                f"Your actual crate enters the tavern pantry. It now holds "
                f"{result['turnips']} portions of turnip. "
                f"Delivery world event {result['event_id']}."
            )
            caller.location.msg_contents(
                f"{caller.key} delivers produce to the shared kitchen.",
                exclude=[caller])
            return
        caller.msg(
            "Use soup | soup prep <base> <seasoning> | soup simmer | "
            "soup notebook | soup procure | soup deliver | soup refuge <hound>."
        )
