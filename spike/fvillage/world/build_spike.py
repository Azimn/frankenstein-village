"""
Build script for the Frankenstein Village spike.
Run with:  evennia shell < spike/world/build_spike.py
(Or: evennia shell, then exec(open('world/build_spike.py').read()))

Idempotent-ish: skips creating things that already exist by key.
"""
from evennia.utils import create, search

ROOM = "typeclasses.rooms.SpikeRoom"
COMMON = "typeclasses.rooms.CommonRoom"
CHAR = "typeclasses.characters.SpikeCharacter"
KEEPER = "typeclasses.characters.Innkeeper"
DOOR = "typeclasses.exits.FrontDoorExit"


def get_or_create_room(key, typeclass, desc, side=None, place=None):
    # NOTE: search_object's typeclass filter matches the exact path, not
    # subclasses — so search by key only and compare exactly.
    found = [o for o in search.search_object(key) if o.key == key]
    if found:
        print(f"room exists: {key}")
        return found[0]
    room = create.create_object(typeclass, key=key)
    room.db.desc = desc
    if side:
        room.tags.add(side, category="side")
    if place:
        room.tags.add(place, category="place")
    print(f"room created: {key}")
    return room


def get_or_create_exit(key, src, dest, typeclass, aliases=()):
    for ex in src.exits:
        # compare destination by id: distinct Python objects may proxy the same row
        if ex.key == key and ex.destination.id == dest.id:
            print(f"exit exists: {key} ({src.key} -> {dest.key})")
            return ex
    ex = create.create_object(typeclass, key=key, location=src, destination=dest, aliases=list(aliases))
    print(f"exit created: {key} ({src.key} -> {dest.key})")
    return ex


# --- rooms -----------------------------------------------------------------
common = get_or_create_room(
    "Inn Common Room", COMMON,
    "The backstage of the world. A low hearth, scarred tables, the smell of "
    "beer and lamp oil. Everything here is out of character: talk about "
    "anything. M. keeps the bar. The front door — the most important object "
    "in the building — stands to the south. A hallway leads east.",
    side="ooc",
)
hallway = get_or_create_room(
    "Inn Hallway", ROOM,
    "A narrow threshold hall. The common room lies west; at the south end, "
    "the front door waits, heavy oak with its brass handle worn bright.",
    side="ooc",
)
square = get_or_create_room(
    "Village Square", ROOM,
    "Cobbles, gaslight, and the smell of wet stone. At the "
    "square's heart a well steams faintly, though the night is cool. The "
    "manor looms on the hill above; the Inn Between stands behind you, "
    "its windows warm. The Blood of the Vine's sign creaks to the east.",
    side="ic",
)
tavern = get_or_create_room(
    "The Blood of the Vine", ROOM,
    "The Blood of the Vine, the village's social hub. A painted sign "
    "outside reads 'Hanul Sangue della Vite'. Long tables, a hearth that "
    "never quite goes out, and talk — always talk. Someone here is always "
    "saying something strange. The village square lies west, through the door.",
    side="ic",
    place="tavern",
)
back_hall = get_or_create_room(
    "Tavern Back Hall", ROOM,
    "A narrow back hall behind the Blood of the Vine. Six guest-room doors stand in "
    "a row beneath low gas jets. The noise of the bar is close to the south.",
    side="ic",
)
lamp_shop = get_or_create_room(
    "The Lamp Shop", ROOM,
    "DeVille's Lamp Shop — though the painted sign says only LAMPS, in gold "
    "leaf. Every surface glows: brass, glass, flames that never seem to need "
    "tending. It smells of beeswax and something sweeter underneath. A "
    "curtained doorway at the back is always closed. Lucian DeVille himself "
    "is always — always — delighted to see you. The village square lies north.",
    side="ic",
    place="shop",
)

# Offstage: where regulars are when their schedule says "home". No exits —
# the churchyard, the cottages, the woods edge don't exist as rooms yet.
# Players never go here; the schedule's observable consequence is that
# people leave and come back.
get_or_create_room(
    "Offstage", ROOM,
    "Behind the village: churchyards and cottages and the woods edge, "
    "all the places the map hasn't drawn yet.",
    side="ic",
    place="offstage",
)

church = get_or_create_room(
    "St. Lazarus Church", ROOM,
    "St. Lazarus Church, stone and candlewax. The nave is narrow and cold; "
    "rows of worn pews face a plain altar with a brass crucifix gone green "
    "at the edges. Behind the altar, a painted wooden panel shows the "
    "raising of Lazarus — the patron, four days dead, sitting up. The "
    "saint's face is turned away. No one remembers voting for that detail. "
    "A confessional box stands in the corner, its curtain drawn. The bell "
    "rope hangs by the door, worn smooth by generations of hands. The "
    "village square lies east.",
    side="ic",
    place="church",
)

# --- exits ------------------------------------------------------------------
# OOC side
get_or_create_exit("east", common, hallway, "evennia.objects.objects.DefaultExit", aliases=["e"])
get_or_create_exit("west", hallway, common, "evennia.objects.objects.DefaultExit", aliases=["w"])
# The threshold. South from the hallway, north back from the square.
get_or_create_exit("south", hallway, square, DOOR, aliases=["s", "door", "front door"])
get_or_create_exit("north", square, hallway, DOOR, aliases=["n"])
get_or_create_exit("north", tavern, back_hall, "evennia.objects.objects.DefaultExit", aliases=["n"])
get_or_create_exit("south", back_hall, tavern, "evennia.objects.objects.DefaultExit", aliases=["s"])
# IC side
get_or_create_exit("east", square, tavern, "evennia.objects.objects.DefaultExit", aliases=["e"])
get_or_create_exit("west", tavern, square, "evennia.objects.objects.DefaultExit", aliases=["w"])
get_or_create_exit("south", square, lamp_shop, "evennia.objects.objects.DefaultExit", aliases=["s"])
get_or_create_exit("north", lamp_shop, square, "evennia.objects.objects.DefaultExit", aliases=["n"])
get_or_create_exit("west", square, church, "evennia.objects.objects.DefaultExit", aliases=["w"])
get_or_create_exit("east", church, square, "evennia.objects.objects.DefaultExit", aliases=["e"])

# --- account-owned private rooms --------------------------------------------
from evennia.accounts.models import AccountDB
from typeclasses.accounts import ensure_private_room

legacy_private_rooms = [
    obj for obj in search.search_object("Private Room")
    if obj.key == "Private Room" and not obj.db.owner_account_id
]

for account in AccountDB.objects.all():
    room = ensure_private_room(account)
    for character in account.characters.all():
        character.home = room
        if character.location in legacy_private_rooms:
            character.move_to(room, quiet=True)

# Remove the old shared room and its public exit after owned rooms exist.
for legacy in legacy_private_rooms:
    for ex in list(common.exits):
        if ex.destination and ex.destination.id == legacy.id:
            ex.delete()
    for obj in list(legacy.contents):
        # Characters were moved above. Anything left is legacy room scenery.
        obj.delete()
    for ex in list(legacy.exits):
        ex.delete()
    legacy.delete()

# --- M. ----------------------------------------------------------------------
found = [o for o in common.contents if o.key == "M."]
if found:
    print("M. already tends the bar.")
    m = found[0]
else:
    m = create.create_object(KEEPER, key="M.", location=common)
    m.db.desc = (
        "The innkeeper. Neither young nor old; the kind of face the village "
        "has been seeing behind bars for longer than anyone admits. Polishes "
        "a glass that is already clean."
    )
    print("M. created in the Inn Common Room.")

# M. answers to "M" as well as "M." — single-letter queries otherwise
# prefix-match player keys ("M" matches "mp_tester1") and talk M breaks.
if "M" not in (m.aliases.all() or []):
    m.aliases.add("M")
    print("M. alias added.")

# Line refresh: fold canon line-bank material (Role 10-adjacent, revoiced
# for M.) into M.'s pools without duplicating what players already saw.
M_TALK_EXTRA = [
    "What happens at the inn stays at the inn. That's not a rule — it's the foundation the rules stand on.",
    "You want to know the village? Sit at the bar for an hour. Everyone tells the truth after the second ale — it's the first one that's all lies.",
]
talk_lines = m.db.talk_lines or []
added = [l for l in M_TALK_EXTRA if l not in talk_lines]
if added:
    talk_lines.extend(added)
    m.db.talk_lines = talk_lines
    print(f"M. talk lines added: {len(added)}")

# --- the Tavern -------------------------------------------------------------
# Upgrade the Tavern to its greeter typeclass (idempotent).
tavern = [o for o in search.search_object("The Blood of the Vine") if o.key == "The Blood of the Vine"][0]
if not tavern.is_typeclass("typeclasses.rooms.TavernRoom", exact=True):
    tavern.swap_typeclass("typeclasses.rooms.TavernRoom", clean_attributes=False)
    print("Tavern upgraded to TavernRoom.")
else:
    print("Tavern already a TavernRoom.")

from typeclasses.characters import KEEPER_DESC
found = [o for o in tavern.contents if o.key == "Bram"]
if found:
    found[0].db.desc = KEEPER_DESC
    print("Bram already keeps the bar (desc re-synced).")
    keeper = found[0]
else:
    keeper = create.create_object(
        "typeclasses.characters.TavernKeeper",
        key="Bram",
        location=tavern,
    )
    keeper.db.desc = KEEPER_DESC
    print("Bram created in the Blood of the Vine.")
# Aliases are set on every run, not just on create — a partial-failure
# rerun must not leave Bram alias-less. (Evennia 6.1: add() takes one
# alias or a list, not multiple args.)
for _a in ["keeper", "the keeper", "tavern keeper",
            "the tavern keeper", "barkeep", "barkeeper", "bram"]:
    if _a not in keeper.aliases.all():
        keeper.aliases.add(_a)

# --- the tavern cat -----------------------------------------------------------
found = [o for o in tavern.contents if o.key == "the tavern cat"]
if found:
    print("The tavern cat already supervises.")
    cat = found[0]
else:
    cat = create.create_object(
        "typeclasses.characters.TavernCat",
        key="the tavern cat",
        location=tavern,
    )
    cat.db.desc = (
        "A smoke-grey cat with one torn ear, supervising the room from "
        "whichever spot currently suits her. She does not speak, which has "
        "never stopped her from having opinions."
    )
    print("Tavern cat created in The Tavern.")
for _a in ["cat", "kitty"]:
    if _a not in cat.aliases.all():
        cat.aliases.add(_a)

from evennia.scripts.models import ScriptDB as _ScriptDB
if _ScriptDB.objects.filter(db_key="cat_life").exists():
    print("cat_life script exists.")
else:
    cat.scripts.add("typeclasses.scripts.CatLife")
    print("cat_life script started.")

# --- ambient life ------------------------------------------------------------
from evennia import create_script
from evennia.scripts.models import ScriptDB

if ScriptDB.objects.filter(db_key="ambient_life").exists():
    print("ambient_life script exists.")
else:
    create_script(
        "typeclasses.scripts.AmbientLife",
        key="ambient_life",
        persistent=True,
    )
    print("ambient_life script created.")

# --- scenery -------------------------------------------------------------------
# Every noun a room description mentions should be examinable — this is a
# mystery game, and examining is how mysteries are solved.


def get_or_create_scenery(key, location, desc, aliases=()):
    found = [o for o in location.contents if o.key == key]
    if found:
        obj = found[0]
    else:
        obj = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key=key, location=location, aliases=list(aliases),
        )
        print(f"scenery created: {key} in {location.key}")
    # Static scenery converges on rebuild. Runtime counters and mutable state
    # live elsewhere and are intentionally preserved.
    obj.db.desc = desc
    for alias in aliases:
        if alias not in (obj.aliases.all() or []):
            obj.aliases.add(alias)
    return obj


# the hanging sign: the Blood of the Vine announces itself (square, eastward)
get_or_create_scenery(
    "a hanging sign", square,
    "A painted wooden sign on creaking chains, pointing east. Gold "
    "vine-leaves curl around words in a careful hand: 'Hanul Sangue della "
    "Vite'. Someone has repainted the leaves recently, and with love.",
    aliases=["sign"],
)


get_or_create_scenery(
    "well", square,
    "The village well at the square's heart. It steams faintly, though "
    "the night is cool. When the air falls still, the vapor rises in a "
    "strangely straight thread. The rope vanishes down into dark water "
    "you can't quite see.",
    aliases=["village well"],
)

# mushrooms by the well: the spike's standing poison item. The `toxic`
# magnitude path in _consume is proven by the bad-stew surprise, but no
# item has used it directly until now. These mushrooms always bite back
# a little — that is the honest deal the damp stones offer. The folklore
# warning is in the desc, so a queasy player has only themselves to blame.
# A bad cap seeds the ledger -> rumor pipeline (consumable-surprise with
# provenance), the same way the stew's bad night does.
found = [o for o in square.contents if o.key == "a cluster of mushrooms"]
if found:
    mushrooms = found[0]
    print("mushrooms already grow by the well.")
else:
    mushrooms = create.create_object(
        "evennia.objects.objects.DefaultObject",
        key="a cluster of mushrooms", location=square,
        aliases=["mushrooms", "cluster", "toadstools"],
    )
    print("mushrooms created: a cluster of mushrooms")
mushrooms.db.desc = (
    "A cluster of pale mushrooms pushing up where the well's damp stones "
    "meet the cobbles. Some are kind and some are not, and only somebody's "
    "grandmother could name each one with confidence."
)
mushrooms.tags.add("consumable")
mushrooms.tags.add("food")  # the eat gate
mushrooms.db.consume = {
    "nourish": 5,
    "toxic": 25,
    "flavor": "You eat a cap. Earthy at first, peppery after — and then "
              "your stomach files a formal complaint. The square has two "
              "of everything for a while.",
    "room": "eats one of the well mushrooms, and goes a remarkable shade "
            "of green.",
    "surprises": [
        {"chance": 25, "key": "kind",
         "text": "A kind one — earthy, peppery, entirely friendly. This "
                 "time. Your stomach only grumbles a little.",
         "room": "eats a well mushroom, and looks relieved to be fine."},
        {"chance": 30, "key": "unkind",
         "text": "The cap is peppery going down and mutinous coming back. "
                 "You sit down on the damp stones and wait for the world "
                 "to settle.",
         "room": "eats a well mushroom and has to sit down on the damp "
                 "stones.",
         "rumor": "Someone ate the mushrooms by the well and spent the "
                  "afternoon green. The keeper's expression did not change.",
         "effect": "queasy"},
    ],
}

# darts & board: the keeper's talk already promises them; now they're real
get_or_create_scenery(
    "darts", tavern,
    "Three brass darts, worn smooth by a hundred hands. (Try: throw darts.)",
    aliases=["dart"],
)
get_or_create_scenery(
    "dartboard", tavern,
    "A scarred board in the corner, the wire gleaming. Three nights running, "
    "someone's darts have all landed in the wire.",
    aliases=["darts"],
)
# The dartboard's old "board" alias now belongs to the price board; fix the
# live object (get_or_create_scenery doesn't touch existing aliases).
_db = [o for o in tavern.contents if o.key == "dartboard"]
if _db and "board" in _db[0].aliases.all():
    _db[0].aliases.remove("board")
    if "darts" not in _db[0].aliases.all():
        _db[0].aliases.add("darts")

# dice cup: the tavern's other house game (roll dice / roll dice vs keeper)
get_or_create_scenery(
    "dice cup", tavern,
    "A leather cup, worn soft as an old boot, holding two bone dice gone "
    "yellow with age. The keeper keeps it behind the bar for anyone with an "
    "idle hour. (Try: roll dice.)",
    aliases=["cup"],
)

# fortune deck: the tavern's corner-table game (draw card)
get_or_create_scenery(
    "a deck of fortune cards", tavern,
    "A worn deck of fortune cards, edges soft from handling, squared neatly "
    "on the corner table. Someone has thumbed the ace of spades nearly "
    "through. (Try: draw card.)",
    aliases=["fortune deck", "deck", "cards"],
)

# the fiddle: hangs on its peg by the hearth, for anyone with the nerve
found = [o for o in tavern.contents if o.key == "a fiddle"]
if not found:
    fiddle = create.create_object(
        "evennia.objects.objects.DefaultObject",
        key="a fiddle", location=tavern, aliases=["fiddle"],
    )
    fiddle.db.desc = (
        "A plain fiddle, varnish worn where chins have rested. It hangs on "
        "its peg by the hearth, waiting for anyone with the nerve. It knows "
        "four airs: 'Barbara Allen', 'The Jolly Waggoner', 'Greensleeves', "
        "and 'The Irish Washerwoman'. (Try: play fiddle <tune>.)"
    )
    print("fiddle created in The Tavern.")
else:
    print("The fiddle already hangs by the hearth.")

# the sideboard: the tavern's help-yourself hospitality (eat / drink)
# Tags are the physics: `consumable` + `food`/`drink`. Magnitudes and the
# surprise table live in db.consume; the eat/drink commands read them.
get_or_create_scenery(
    "a sideboard", tavern,
    "A long sideboard laden with the tavern's fare: bread, cheese, "
    "a pot of stew, ale, wine, water. The price board on the wall says "
    "what coin buys. (Try: eat bread. Or: drink ale.)",
    aliases=["sideboard"],
)

# the price board: Jay's ruling, 2026-10-04 — coin, with a price list on
# the wall. 1890 Austria-Hungary: forint, 1 ft = 100 krajczár. Bram chalks
# it himself; the figures match TAVERN_PRICES in village_cmds.py.
get_or_create_scenery(
    "a chalked price board", tavern,
    "Chalked on the board in Bram's blocky hand:\n"
    "  bread ...... 4 kr\n"
    "  cheese ..... 6 kr\n"
    "  stew ...... 12 kr\n"
    "  ale ........ 5 kr\n"
    "  wine ...... 10 kr\n"
    "  water ..... free\n"
    "Underneath, underlined twice: COIN FIRST.",
    aliases=["board", "price board", "prices", "price list"],
)
# The sideboard's old "help yourself" text predates coin; refresh it.
_sb = [o for o in tavern.contents if o.key == "a sideboard"]
if _sb:
    _sb[0].db.desc = (
        "A long sideboard laden with the tavern's fare: bread, cheese, "
        "a pot of stew, ale, wine, water. The price board on the wall says "
        "what coin buys. (Try: eat bread. Or: drink ale.)"
    )


# Servings live in the consume dict as `servings_max`; the live count is
# db.servings. Only the keeper's restock refills — a rebuild never resets
# mid-session counts (init only if never set). Water has no servings_max:
# well water is free and infinite by design. The well mushrooms aren't
# _fare at all — they're wild, not the keeper's board.
def _fare(key, aliases, kind, desc, consume, servings=None, short=None):
    found = [o for o in tavern.contents if o.key == key]
    if found:
        obj = found[0]
    else:
        obj = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key=key, location=tavern, aliases=list(aliases),
        )
        print(f"fare created: {key}")
    obj.db.desc = desc
    obj.tags.add("consumable")
    obj.tags.add(kind)  # "food" or "drink" — the eat/drink gate
    obj.db.consume = dict(consume)
    if servings is not None:
        obj.db.consume["servings_max"] = servings
        if short:
            obj.db.consume["short"] = short
        if obj.db.servings is None:
            obj.db.servings = servings
    return obj


_fare(
    "a loaf of bread", ["bread", "loaf"], "food",
    "Dark rye, still warm from the morning bake. Someone knows their oven.",
    {
        "nourish": 25,
        "flavor": "You tear off a hunk of rye. Warm, honest, gone too soon.",
        "room": "tears into the rye bread.",
        "surprises": [
            {"chance": 6, "key": "stale",
             "text": "This bread has seen better days — dry as a sermon.",
             "room": "makes a face at the bread.",
             "effect": "nonourish"},
        ],
    },
    servings=6, short="bread",
)
_fare(
    "a wedge of cheese", ["cheese", "wedge"], "food",
    "Hard cheese, sharp enough to argue with.",
    {
        "nourish": 15,
        "flavor": "The cheese bites back a little. You respect that.",
        "room": "works through a wedge of the sharp cheese.",
    },
    servings=5, short="cheese",
)
_fare(
    "a bowl of stew", ["stew", "bowl"], "food",
    "Thick stew, mostly root vegetables. The meat's provenance is uncertain, "
    "and the keeper changes the subject when asked.",
    {
        "nourish": 40,
        "flavor": "The stew is thick, peppery, and — you decide not to ask.",
        "room": "spoons up the stew without asking questions.",
        "surprises": [
            {"chance": 5, "key": "coin",
             "text": "You bite down on something hard — a copper coin, worn "
                     "smooth! Lucky stew.",
             "room": "bites down on something hard, and grins.",
             "effect": "coin"},
            {"chance": 6, "key": "off",
             "text": "Something in this stew was... ambitious. Your stomach "
                     "turns.",
             "room": "goes a little green around the edges.",
             "rumor": "Don't eat the stew on Thursdays. Just don't.",
             "effect": "queasy"},
        ],
    },
    servings=8, short="stew",
)
_fare(
    "a tankard of ale", ["ale", "tankard"], "drink",
    "House ale, foamy and honest. Mostly honest.",
    {
        "nourish": 5, "alcohol": 25,
        "flavor": "The ale is foamy and forthright.",
        "room": "takes a long pull of ale.",
        "surprises": [
            {"chance": 8, "key": "watered",
             "text": "This tastes thin. Watered, unless your tongue's lying. "
                     "The keeper avoids your eye.",
             "room": "sniffs at the ale suspiciously.",
             "rumor": "The keeper waters the ale. Or so the talk goes."},
        ],
    },
    servings=8, short="ale",
)
_fare(
    "a cup of wine", ["wine", "cup"], "drink",
    "Red wine, better than it has any right to be at this price.",
    {
        "alcohol": 40,
        "flavor": "The wine is dark and unhurried.",
        "room": "sips the wine with undue ceremony.",
        "surprises": [
            {"chance": 6, "key": "vintage",
             "text": "This is... actually remarkable. Blackcurrant, old "
                     "wood, something like forgiveness.",
             "room": "closes their eyes over the wine.",
             "effect": "heal"},
        ],
    },
    servings=6, short="wine",
)
_fare(
    "a cup of water", ["water", "cup"], "drink",
    "Cold well water. Free, honest, and — the regulars will tell you — "
    "strategically useful.",
    {
        "sobering": 15,
        "flavor": "Cold water. It clears the head and steadies the hands.",
        "room": "drinks a full cup of water, deliberately.",
    },
)

# --- the lamp shop: Lucian DeVille -------------------------------------------
# He says he sells lamps. The lamps are real. Everything else has a price
# that isn't money. His one genuine emotion is fury at the antiquarian
# whose shop hasn't even opened yet — a man completely indifferent to him.
# Upgrade the Lamp Shop to its greeter typeclass (idempotent).
if not lamp_shop.is_typeclass("typeclasses.rooms.LampShopRoom", exact=True):
    lamp_shop.swap_typeclass("typeclasses.rooms.LampShopRoom", clean_attributes=False)
    print("Lamp Shop upgraded to LampShopRoom.")
_luc = [o for o in lamp_shop.contents if o.key == "Lucian DeVille"]
_LUCIAN_DESC = (
    "Lucian DeVille, in a waistcoat the color of lamplight. His smile "
    "arrives before he does and lingers after he's turned away. His "
    "hands are clean — remarkably clean, for a man who handles oil and "
    "brass all day. He is, by every account in town, the nicest person "
    "in it."
)
if _luc:
    _luc[0].db.desc = _LUCIAN_DESC
    print("Lucian DeVille already minds the shop (desc re-synced).")
    lucian = _luc[0]
else:
    lucian = create.create_object(
        "typeclasses.characters.LucianDeVille",
        key="Lucian DeVille",
        location=lamp_shop,
    )
    lucian.db.desc = _LUCIAN_DESC
    print("Lucian DeVille created in The Lamp Shop.")
for _a in ["lucian", "deville", "shopkeeper", "lamp seller", "lampseller"]:
    if _a not in lucian.aliases.all():
        lucian.aliases.add(_a)


def _curio(key, aliases, desc):
    found = [o for o in lamp_shop.contents if o.key == key]
    if found:
        obj = found[0]
    else:
        obj = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key=key, location=lamp_shop, aliases=list(aliases),
        )
        print(f"curio created: {key}")
    obj.db.desc = desc
    return obj


_curio(
    "a brass lamp", ["brass lamp", "lamp"],
    "A brass lamp, polished to a warm glow. The tag, in Lucian's careful "
    "hand: 'Never needs oil. Never gutters. Some things are exactly what "
    "they claim to be.'",
)
_curio(
    "a silver pocket watch", ["pocket watch", "watch", "silver watch"],
    "A silver pocket watch, cool to the touch. The hands don't keep the "
    "hour — they keep the hour you most need. The price tag, in Lucian's "
    "careful hand, reads only: 'One truth about your neighbor.' No one "
    "has yet settled what a truth is worth here, or to whom it would "
    "be told. Lucian is in no hurry to decide.",
)
_curio(
    "a black candle", ["black candle", "candle"],
    "A black candle, never lit, and not for lighting — ask Lucian and "
    "he only smiles. The tag reads: 'Light this, and hear what "
    "the village says about you when you leave the room.' Below, in smaller "
    "script: 'Not for sale. Not yet.'",
)

# --- the regulars: the room's memory ------------------------------------------
# Authored persons with seats, pasts, and opinions about each other. The
# TavernLife ticker moves them through beats; they eat and drink through
# the same pipeline players use.


def _regular(key, aliases, regular_key, desc):
    # Search GLOBALLY: the routine ticker moves regulars, so a tavern-only
    # check creates duplicates on rebuild. (2026-10-04: doubled the cast.)
    found = [o for o in search.search_object(key) if o.key == key]
    if found:
        obj = found[0]
    else:
        obj = create.create_object(
            "typeclasses.characters.TavernRegular",
            key=key, location=tavern, aliases=list(aliases),
        )
        print(f"regular created: {key}")
    obj.db.regular_key = regular_key
    obj.db.desc = desc
    return obj


_regular(
    "Old Vasile", ["vasile", "old vasile"], "vasile",
    "Old Vasile, folded into the corner like a coat left behind. His hands "
    "are gravedigger's hands — he doesn't dig anymore, but the hands didn't "
    "get the word. He drinks ale, always the same corner, and knows where "
    "the bodies are buried. More importantly, he knows where they aren't.",
)
_regular(
    "Magda", ["magda"], "magda",
    "Magda, sleeves rolled, arms that could wring a confession out of a "
    "sheet. She does the washing for half the town and knows whose linen "
    "tells stories. She trades rumor for rumor, and always collects.",
)
_regular(
    "János", ["janos", "jános"], "janos",
    "János, broad as a door and quiet as one, when he chooses. A Hound — a "
    "monster hunter — between contracts. His kit bag sits by his feet, "
    "packed. It's always packed. He drinks like the world's ending, because "
    "for some villages, it is.",
)

# --- the confessional ---------------------------------------------------------
# A fixture, not furniture: the box hears. The confess command does the work.


def _fixture(key, aliases, location, desc):
    found = [o for o in location.contents if o.key == key]
    if found:
        obj = found[0]
    else:
        obj = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key=key, location=location, aliases=list(aliases),
        )
        print(f"fixture created: {key}")
    obj.db.desc = desc
    return obj


_church = [o for o in search.search_object("St. Lazarus Church")
           if o.key == "St. Lazarus Church"][0]
_fixture(
    "a confessional box", ["confessional", "box"],
    _church,
    "A wooden confessional box in the corner, curtain drawn. The kneeler "
    "is worn down the middle by generations of knees. The left panel smells "
    "faintly of lavender, though there is no lavender in the church. What's "
    "said in there stays in there; that's the whole of the sacrament and the "
    "whole of the burden. (Try: confess <words>.)",
)

# Canon incident #6 is a live environmental hook, not a quest marker. The
# strongbox and roll expose separate evidence channels through ordinary look.
def _incident_fixture(key, aliases, typeclass):
    found = [o for o in _church.contents if o.key == key]
    if found:
        obj = found[0]
    else:
        obj = create.create_object(
            typeclass,
            key=key,
            location=_church,
            aliases=list(aliases),
        )
        print(f"incident fixture created: {key}")
    for alias in aliases:
        if alias not in (obj.aliases.all() or []):
            obj.aliases.add(alias)
    return obj


_incident_fixture(
    "the tithe strongbox",
    ["strongbox", "tithe box", "church strongbox"],
    "typeclasses.objects.TitheStrongbox",
)
_incident_fixture(
    "the tithe roll",
    ["roll", "tithe ledger", "parish roll"],
    "typeclasses.objects.TitheRoll",
)

# --- Father Andrei --------------------------------------------------------------
# The priest of St. Lazarus. A TavernRegular by machinery — schedule,
# greet/talk rotation, tavern beats — though his seat is the church.


def _andrei():
    found = [o for o in _church.contents if o.key == "Father Andrei"]
    if found:
        obj = found[0]
    else:
        # He may have been created in the tavern by an earlier build; find
        # him anywhere before making a second one.
        elsewhere = [
            o for o in search.search_object("Father Andrei")
            if o.key == "Father Andrei"
        ]
        if elsewhere:
            obj = elsewhere[0]
        else:
            obj = create.create_object(
                "typeclasses.characters.FatherAndrei",
                key="Father Andrei", location=_church,
                aliases=["andrei", "father", "priest"],
            )
            print("regular created: Father Andrei")
    obj.db.regular_key = "andrei"
    obj.db.desc = (
        "Father Andrei, priest of St. Lazarus. Late forties, going grey at "
        "the temples, hands that have buried half the village. He keeps the "
        "calendar because the village needs the calendar; whether he still "
        "believes the rope he's holding is anybody's guess, including his."
    )
    return obj


_andrei()

# The common room's description claimed the front door "stands to the
# south", but the door is only reachable via the hallway (east). Fix the
# description to match the layout.
common.db.desc = (
    "The backstage of the world. A low hearth, scarred tables, the smell of "
    "beer and lamp oil. Everything here is out of character: talk about "
    "anything. M. keeps the bar. A hallway leads east — at its south end "
    "stands the front door, the most important object in the building."
)

# --- prose-audit convergence (2026-10-02) -----------------------------------
# Descriptions and NPC line pools are only set at creation; this block
# re-syncs the live objects with the canonical text so prose fixes land
# without wiping the DB. Idempotent.
from typeclasses.characters import (
    INNKEEPER_GREETS, INNKEEPER_TALKS, KEEPER_DESC, KEEPER_GREETS,
    KEEPER_TALKS,
)

for _private in [
    o for o in search.search_object("Private Room")
    if o.key == "Private Room" and o.db.owner_account_id
]:
    _private.db.desc = (
        "Your room at the Inn Between. It is private and it persists; no one "
        "else can enter. A short guide lies on the nightstand. Stairs lead down."
    )
_tavern = [o for o in search.search_object("The Blood of the Vine") if o.key == "The Blood of the Vine"][0]
_tavern.db.desc = (
    "The Blood of the Vine, the village's social hub. A painted sign "
    "outside reads 'Hanul Sangue della Vite'. Long tables, a hearth that "
    "never quite goes out, and talk — always talk. Someone here is always "
    "saying something strange. The village square lies west, through the door."
)
_m = [o for o in search.search_object("M.") if o.key == "M."]
if _m:
    _m[0].db.greet_lines = list(INNKEEPER_GREETS)
    _m[0].db.talk_lines = list(INNKEEPER_TALKS)
    print("M. line pools re-synced.")
_k = [o for o in _tavern.contents if o.key == "Bram"]
if _k:
    _k[0].db.desc = KEEPER_DESC
    _k[0].db.greet_lines = list(KEEPER_GREETS)
    _k[0].db.talk_lines = list(KEEPER_TALKS)
    print("Keeper line pools re-synced.")
print("Prose convergence done.")

# --- the Room Six mystery ---------------------------------------------------
# The register on M.'s bar (the hook) and Room Six's door in the hallway
# (the investigation). The note itself spawns per-player on first close
# look at the door. World flags live on the room_six script.


def get_or_create_typed(key, location, typeclass, aliases=()):
    found = [o for o in location.contents if o.key == key]
    if found:
        return found[0]
    obj = create.create_object(typeclass, key=key, location=location,
                               aliases=list(aliases))
    print(f"created: {key} ({typeclass}) in {location.key}")
    return obj


def relocate_or_create_typed(key, location, typeclass, aliases=()):
    """Move a unique typed object to its canonical location or create it."""
    found = [
        o for o in search.search_object(key)
        if o.key == key and o.typeclass_path == typeclass
    ]
    if found:
        obj = found[0]
        if obj.location != location:
            obj.move_to(location, quiet=True)
            print(f"moved: {key} -> {location.key}")
    else:
        obj = create.create_object(
            typeclass, key=key, location=location, aliases=list(aliases)
        )
        print(f"created: {key} ({typeclass}) in {location.key}")
    for alias in aliases:
        if alias not in (obj.aliases.all() or []):
            obj.aliases.add(alias)
    return obj

register = relocate_or_create_typed(
    "register", tavern, "typeclasses.objects.Register", aliases=["guest book"]
)
from typeclasses.objects import REGISTER_DESC
register.db.desc = REGISTER_DESC
room_six_door = relocate_or_create_typed(
    "Room Six door", back_hall, "typeclasses.objects.RoomSixDoor",
    aliases=["sixth door"],
)

# Canonical event history is created before any mystery projection scripts.
if ScriptDB.objects.filter(db_key="rumor_registry").exists():
    print("rumor_registry script exists.")
else:
    create_script(
        "typeclasses.scripts.RumorRegistry",
        key="rumor_registry",
        persistent=True,
    )
    print("rumor_registry script created.")

# Only IC residents who can actually exchange gossip join the rumor network.
# M. is deliberately absent: NPCs must never perceive the OOC layer.
for _ooc_m in [o for o in search.search_object("M.") if o.key == "M."]:
    _ooc_m.tags.remove("participant", category="rumor")

_rumor_profiles = {
    "Bram": (0.65, 0.45),
    "Old Vasile": (0.35, 0.30),
    "Magda": (0.90, 0.65),
    "János": (0.45, 0.25),
    "Father Andrei": (0.50, 0.35),
    "Lucian DeVille": (0.75, 0.55),
}
_rumor_participants = []
for _name, (_curiosity, _gullibility) in _rumor_profiles.items():
    _found = [o for o in search.search_object(_name) if o.key == _name]
    if not _found:
        continue
    _npc = _found[0]
    _npc.tags.add("participant", category="rumor")
    _npc.db.rumor_curiosity = _curiosity
    _npc.db.rumor_gullibility = _gullibility
    _rumor_participants.append(_npc)

from world.rumors import seed_playable_rumors
_seeded_rumors = seed_playable_rumors(participants=_rumor_participants)
print(f"rumor roots ready: {len(_seeded_rumors)} playable canon seeds.")

if ScriptDB.objects.filter(db_key="world_event_ledger").exists():
    print("world_event_ledger script exists.")
else:
    create_script(
        "typeclasses.scripts.WorldEventLedger",
        key="world_event_ledger",
        persistent=True,
    )
    print("world_event_ledger script created.")

if ScriptDB.objects.filter(db_key="room_six").exists():
    print("room_six script exists.")
else:
    create_script(
        "typeclasses.scripts.RoomSixMystery",
        key="room_six",
        persistent=True,
    )
    print("room_six script created.")

# Reports are records for staff review, never an automatic punishment system.
if ScriptDB.objects.filter(db_key="moderation_queue").exists():
    print("moderation_queue script exists.")
else:
    create_script(
        "typeclasses.scripts.ModerationQueue",
        key="moderation_queue",
        persistent=True,
    )
    print("moderation_queue script created.")

# --- seats --------------------------------------------------------------------
# sit/stand furniture: the bar, the hearth, the usual table. Seats are a
# typed object (typeclasses.objects.Seat); the sit/stand commands own the
# posture logic. Idempotent: phrases and descriptions re-apply on every run
# so prose fixes land without wiping the DB.
#
# Seat keys are BARE nouns ("bar", not "the bar"): Evennia's look listing
# prepends its own article ("a bar"), so keyed articles double up
# ("a the bar"). The full sit phrase ("at the bar") lives in db.sit_phrase.
#
# Migration 2026-10-03: the first pass created seats with keyed articles;
# rename them in place.
_SEAT_RENAMES = {
    "the bar": "bar",
    "the hearth": "hearth",
    "the usual table": "usual table",
    "a scarred table": "scarred table",
}
for _room in (common, tavern):
    for _o in list(_room.contents):
        if _o.key in _SEAT_RENAMES and _o.is_typeclass(
            "typeclasses.objects.Seat", exact=True
        ):
            _o.key = _SEAT_RENAMES[_o.key]
            print(f"seat renamed: {_o.key}")
SEATS = [
    # (key, location, phrase, aliases, desc)
    ("bar", tavern, "at the bar", ["the bar"],
     "The long bar, dark wood worn pale along its edge by a hundred hands. "
     "The keeper works this side; the other side is yours. (Try: sit bar.)"),
    ("hearth", tavern, "by the hearth", ["the hearth", "fire"],
     "The hearth that never quite goes out. A low stone bench runs along "
     "it — the warmest seat in the village. (Try: sit hearth.)"),
    ("usual table", tavern, "at the usual table", ["the usual table", "table"],
     "A corner table, scarred and comfortable. The regulars call it the "
     "usual table, though no one agrees whose it is. (Try: sit table.)"),
    ("hearth", common, "by the hearth", ["the hearth", "fire"],
     "The inn's hearth, low and steady. A settle bench faces it — the "
     "backstage seat. (Try: sit hearth.)"),
    ("scarred table", common, "at a scarred table", ["a scarred table", "table"],
     "Scarred tables, worn by years of mugs and elbows. (Try: sit table.)"),
]
for _key, _loc, _phrase, _aliases, _desc in SEATS:
    _seat = get_or_create_typed(
        _key, _loc, "typeclasses.objects.Seat", aliases=_aliases)
    _seat.db.sit_phrase = _phrase
    _seat.db.desc = _desc
print("seats set.")

# --- senses -------------------------------------------------------------------
# The village is not visual-only. Every room carries persistent air and
# sound; the square's weather line is owned by the weather script.
SENSES = {
    "Private Room": (
        "The air is close and warm, smelling of clean linen and lamp oil.",
        "The inn settles around you: a creak, a sigh, then quiet.",
    ),
    "Inn Common Room": (
        "The air is warm with woodsmoke, spilled beer, and lamp oil.",
        "The hearth mutters; M.'s glass squeaks under her cloth.",
    ),
    "Inn Hallway": (
        "The air is cold and still, smelling faintly of lamp oil and old wood.",
        "Floorboards tick as they cool. Six doors keep their own counsel.",
    ),
    "Village Square": (
        "The air is cold and damp. Gaslight hisses at the square's heart.",
        "Cobbles hold the echo of footsteps long gone; the well steams faintly.",
    ),
    "The Blood of the Vine": (
        "The air is warm — woodsmoke, stew, beer, and the particular perfume of talk.",
        "Talk laps at every table; the fire pops; someone laughs too loud.",
    ),
    "Tavern Back Hall": (
        "The air is cooler here, touched by lamp oil and old plaster.",
        "The Tavern murmurs through the wall; the six doors answer with silence.",
    ),
}
for _key, (_air, _sound) in SENSES.items():
    _rooms = [o for o in search.search_object(_key) if o.key == _key]
    for _room in _rooms:
        _room.db.sense_air = _air
        _room.db.sense_sound = _sound
print("senses set.")

# Room Six's door keeps its own counsel — audibly.
_door = [o for o in back_hall.contents if o.key == "Room Six door"]
if _door:
    _door[0].db.listen_line = (
        "Beyond the door: nothing. Which is itself a kind of answer."
    )
    print("door listen line set.")

# --- village time & weather ---------------------------------------------------
for _skey, _sclass in (
    ("village_time", "typeclasses.scripts.VillageTime"),
    ("village_weather", "typeclasses.scripts.VillageWeather"),
    ("resident_population", "typeclasses.scripts.ResidentPopulationRegistry"),
    ("public_records", "typeclasses.scripts.PublicRecordRegistry"),
    ("situation_registry", "typeclasses.scripts.SituationRegistry"),
    ("warmth_watch", "typeclasses.scripts.WarmthWatch"),
    ("tavern_life", "typeclasses.scripts.TavernLife"),
    ("village_routine", "typeclasses.scripts.VillageRoutine"),
):
    if ScriptDB.objects.filter(db_key=_skey).exists():
        print(f"{_skey} script exists.")
    else:
        create_script(_sclass, key=_skey, persistent=True)
        print(f"{_skey} script created.")
# Materialize or register the persistent resident population only after
# village time exists, so first placement resolves against the actual clock.
from world.residents import ensure_population
_population = ensure_population()
print(
    "resident population ready: "
    f"{_population['population_size']} residents "
    f"({_population['created']} created, {_population['registered']} registered)."
)

from world.situations import ensure_situations
_situations = ensure_situations()
print(
    "situation registry ready: "
    f"{_situations['count']} situations "
    f"({_situations['created']} created)."
)

# The square starts under fog, as it has always been.
_square = [o for o in search.search_object("Village Square") if o.key == "Village Square"][0]
if not _square.db.weather_sense:
    _square.db.weather_sense = "Fog deadens every sound; the gaslight is a smear."
    print("square weather sense initialized.")

print("Spike build complete.")
