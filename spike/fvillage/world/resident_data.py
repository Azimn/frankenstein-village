"""Immutable production definitions for the resident population.

This module is deliberately free of Evennia imports so the same schedules can
be exercised by offline simulation. Mutable state never belongs here.
"""

from __future__ import annotations


SCHEMA_VERSION = 1

LOCATION_PROJECTIONS = {
    "village_square": "Village Square",
    "tavern": "The Blood of the Vine",
    "church": "St. Lazarus Church",
    "lamp_shop": "The Lamp Shop",
    "inn_common": "Inn Common Room",
    "tavern_back_hall": "Tavern Back Hall",
    "offstage": "Offstage",
    # Unbuilt logical places project Offstage without becoming the same place.
    "schoolhouse": "Offstage",
    "bakery": "Offstage",
    "vessey_nursery": "Offstage",
    "forge": "Offstage",
    "bell_house": "Offstage",
    "woods": "Offstage",
    "fields": "Offstage",
    "butcher_shop": "Offstage",
    "harbinger_office": "Offstage",
    "carpenter_shop": "Offstage",
    "midwife_rounds": "Offstage",
    "night_watch_post": "Offstage",
}

INTEREST_POOL = (
    "horses",
    "gardening",
    "local history",
    "church music",
    "folk stories",
    "boxing",
    "poetry",
    "mechanical devices",
    "mushroom gathering",
    "cards",
    "bird watching",
    "funeral customs",
    "astronomy",
    "herbalism",
    "hunting",
    "embroidery",
    "theater",
    "foreign newspapers",
    "ghost stories",
    "stage magic",
    "weather lore",
    "wood carving",
    "old maps",
    "beekeeping",
)


# Schedules use half-open hour ranges. Midnight-wrapping blocks are split.
SCHEDULES = {
    "child_school": (
        (0, 7, "home", "sleeps"),
        (7, 8, "village_square", "walks toward school"),
        (8, 15, "schoolhouse", "attends lessons"),
        (15, 16, "village_square", "walks home from school"),
        (16, 24, "home", "spends the evening at home"),
    ),
    "schoolteacher": (
        (0, 7, "home", "sleeps"),
        (7, 8, "village_square", "walks to the schoolhouse"),
        (8, 16, "schoolhouse", "teaches the village children"),
        (16, 17, "village_square", "walks home with papers under one arm"),
        (17, 24, "home", "marks lessons and keeps her own evening"),
    ),
    "baker_master": (
        (0, 4, "home", "sleeps"),
        (4, 13, "bakery", "works the ovens"),
        (13, 15, "village_square", "takes deliveries and trades news"),
        (15, 21, "home", "keeps the household"),
        (21, 24, "home", "sleeps"),
    ),
    "baker_household": (
        (0, 5, "home", "sleeps"),
        (5, 14, "bakery", "works the bakery"),
        (14, 16, "village_square", "runs errands"),
        (16, 22, "home", "keeps the household"),
        (22, 24, "home", "sleeps"),
    ),
    "baker_doorway": (
        (0, 6, "home", "sleeps"),
        (6, 15, "bakery", "sells bread at the doorway"),
        (15, 17, "village_square", "runs the last orders"),
        (17, 24, "home", "stays with family"),
    ),
    "flower_seller": (
        (0, 6, "home", "sleeps"),
        (6, 7, "vessey_nursery", "cuts the morning flowers"),
        (7, 16, "village_square", "keeps the flower stall"),
        (16, 18, "vessey_nursery", "puts the beds in order"),
        (18, 24, "home", "spends the evening at home"),
    ),
    "gardener": (
        (0, 5, "home", "sleeps"),
        (5, 12, "vessey_nursery", "tends the nursery beds"),
        (12, 14, "village_square", "takes a midday round"),
        (14, 19, "vessey_nursery", "works the outer beds"),
        (19, 24, "home", "stays home"),
    ),
    "smith": (
        (0, 6, "home", "sleeps"),
        (6, 18, "forge", "works at the forge"),
        (18, 19, "village_square", "crosses the square after work"),
        (19, 24, "home", "rests at home"),
    ),
    "healer": (
        (0, 7, "home", "sleeps"),
        (7, 12, "bell_house", "sees patients and prepares remedies"),
        (12, 15, "village_square", "makes rounds through the village"),
        (15, 20, "bell_house", "keeps the remedy room"),
        (20, 24, "home", "rests"),
    ),
    "hunter": (
        (0, 5, "home", "sleeps"),
        (5, 15, "woods", "checks snares and the marsh road"),
        (15, 18, "village_square", "trades game and news"),
        (18, 22, "tavern", "takes an evening drink"),
        (22, 24, "home", "sleeps"),
    ),
    "well_keeper": (
        (0, 4, "home", "sleeps"),
        (4, 9, "village_square", "sweeps the square and tends the well"),
        (9, 16, "home", "keeps his own hours"),
        (16, 19, "village_square", "returns to the well before dusk"),
        (19, 24, "home", "stays home"),
    ),
    "butcher": (
        (0, 5, "home", "sleeps"),
        (5, 6, "village_square", "walks to open the butcher shop"),
        (6, 18, "butcher_shop", "keeps the butcher shop"),
        (18, 19, "village_square", "closes up and heads home"),
        (19, 24, "home", "rests at home"),
    ),
    "butcher_assistant": (
        (0, 6, "home", "sleeps"),
        (6, 7, "village_square", "walks to work"),
        (7, 18, "butcher_shop", "works for the butcher"),
        (18, 20, "village_square", "runs errands after work"),
        (20, 24, "home", "stays home"),
    ),
    "farmer": (
        (0, 5, "home", "sleeps"),
        (5, 6, "village_square", "crosses the village toward the fields"),
        (6, 18, "fields", "works the fields"),
        (18, 19, "village_square", "walks home from the fields"),
        (19, 24, "home", "eats and sleeps"),
    ),
    "farm_household": (
        (0, 6, "home", "sleeps"),
        (6, 11, "fields", "works near the farmstead"),
        (11, 14, "village_square", "does the market round"),
        (14, 18, "fields", "finishes the day's farm work"),
        (18, 24, "home", "keeps the household"),
    ),
    "lamplighter": (
        (0, 10, "home", "sleeps"),
        (10, 15, "village_square", "checks glass and mantles"),
        (15, 17, "home", "rests before the evening round"),
        (17, 24, "village_square", "lights and tends the street lamps"),
    ),
    "recluse": (
        (0, 11, "home", "keeps to himself"),
        (11, 13, "village_square", "buys what he cannot make"),
        (13, 24, "home", "keeps to himself"),
    ),
    "chronicler": (
        (0, 7, "home", "sleeps"),
        (7, 12, "harbinger_office", "sorts reports and copies notices"),
        (12, 15, "village_square", "collects names, dates, and corrections"),
        (15, 19, "harbinger_office", "writes the afternoon copy"),
        (19, 22, "tavern", "listens more than she speaks"),
        (22, 24, "home", "sleeps"),
    ),
    "seamstress": (
        (0, 6, "home", "sleeps"),
        (6, 12, "home", "sews by the window"),
        (12, 15, "village_square", "delivers mending and takes new work"),
        (15, 21, "home", "returns to her needlework"),
        (21, 24, "home", "sleeps"),
    ),
    "carpenter": (
        (0, 6, "home", "sleeps"),
        (6, 18, "carpenter_shop", "works timber and repairs"),
        (18, 20, "tavern", "takes supper and one drink"),
        (20, 24, "home", "rests"),
    ),
    "midwife": (
        (0, 6, "home", "sleeps unless called"),
        (6, 11, "midwife_rounds", "makes household rounds"),
        (11, 14, "village_square", "takes messages and buys supplies"),
        (14, 20, "midwife_rounds", "continues her rounds"),
        (20, 24, "home", "stays within calling distance"),
    ),
    "night_watch": (
        (0, 5, "night_watch_post", "walks the night watch"),
        (5, 13, "home", "sleeps"),
        (13, 18, "village_square", "keeps ordinary daytime errands"),
        (18, 22, "home", "rests before duty"),
        (22, 24, "night_watch_post", "begins the night watch"),
    ),
    "lamp_shopkeeper": (
        (0, 8, "home", "sleeps"),
        (8, 9, "village_square", "walks to the shop"),
        (9, 18, "lamp_shop", "keeps the Lamp Shop"),
        (18, 20, "village_square", "takes the evening air"),
        (20, 24, "home", "keeps his own counsel"),
    ),
}


def _resident(
    stable_id,
    display_name,
    *,
    age_band,
    gender,
    household,
    occupation,
    schedule,
    kin=(),
    traits=(),
    faction=None,
    role_bound=False,
    provenance="project_original_2026_10_05",
    existing_key=None,
    schedule_engine="population",
    home=None,
):
    return {
        "stable_id": stable_id,
        "display_name": display_name,
        "age_band": age_band,
        "gender": gender,
        "household_id": household,
        "home_id": home or f"home:{household}",
        "occupation": occupation,
        "faction": faction,
        "schedule_id": schedule,
        "kin": tuple(kin),
        "traits": tuple(traits),
        "role_bound": bool(role_bound),
        "provenance": provenance,
        "existing_key": existing_key,
        "schedule_engine": schedule_engine,
    }


RESIDENTS = (
    # Existing authored residents. Their custom routines remain authoritative.
    _resident("bram_v", "Bram", age_band="adult", gender="man",
              household="bram_v", occupation="tavern keeper", schedule="none",
              traits=("observant", "dry"), role_bound=True,
              provenance="runtime_canon", existing_key="Bram",
              schedule_engine="legacy"),
    _resident("old_vasile", "Old Vasile", age_band="elder", gender="man",
              household="vasile", occupation="retired gravedigger",
              schedule="none", traits=("watchful", "stubborn"),
              provenance="runtime_canon", existing_key="Old Vasile",
              schedule_engine="legacy"),
    _resident("magda", "Magda", age_band="adult", gender="woman",
              household="magda", occupation="washerwoman",
              schedule="none", traits=("sociable", "curious"),
              provenance="runtime_canon", existing_key="Magda",
              schedule_engine="legacy"),
    _resident("janos", "János", age_band="adult", gender="man",
              household="janos", occupation="Hound",
              schedule="none", traits=("watchful", "practical"), faction="Hounds",
              provenance="runtime_canon", existing_key="János",
              schedule_engine="legacy"),
    _resident("father_andrei", "Father Andrei", age_band="adult", gender="man",
              household="rectory", occupation="priest", schedule="none",
              traits=("devout", "skeptical"), faction="St. Lazarus",
              provenance="runtime_canon", existing_key="Father Andrei",
              schedule_engine="legacy"),
    _resident("lucian_deville", "Lucian DeVille", age_band="adult", gender="man",
              household="deville", occupation="lamp shopkeeper",
              schedule="lamp_shopkeeper", traits=("courteous", "territorial"),
              role_bound=True, provenance="runtime_canon",
              existing_key="Lucian DeVille", schedule_engine="population"),

    # Genealogy v0.1 households, corrected only where newer canon supersedes it.
    _resident("bram_marrow", "Bram Marrow", age_band="adult", gender="man",
              household="marrow", occupation="master baker", schedule="baker_master",
              kin=("tess_marrow","pip_marrow","nan_marrow","widow_marrow"),
              traits=("industrious","protective"), role_bound=True,
              provenance="genealogy_v0_1"),
    _resident("tess_marrow", "Tess Marrow", age_band="adult", gender="woman",
              household="marrow", occupation="bakery bookkeeper",
              schedule="baker_household",
              kin=("bram_marrow","pip_marrow","nan_marrow","widow_marrow"),
              traits=("practical","protective"), provenance="genealogy_v0_1"),
    _resident("pip_marrow", "Pip Marrow", age_band="young_adult", gender="man",
              household="marrow", occupation="baker apprentice",
              schedule="baker_household",
              kin=("bram_marrow","tess_marrow","nan_marrow","widow_marrow"),
              traits=("restless","curious"), faction="hunter-curious",
              provenance="genealogy_v0_1"),
    _resident("nan_marrow", "Nan Marrow", age_band="teen", gender="woman",
              household="marrow", occupation="bread seller",
              schedule="baker_doorway",
              kin=("bram_marrow","tess_marrow","pip_marrow","widow_marrow"),
              traits=("observant","sociable"), provenance="genealogy_v0_1"),
    _resident("widow_marrow", "Old Widow Marrow", age_band="elder", gender="woman",
              household="marrow", occupation="retired baker", schedule="recluse",
              kin=("bram_marrow","tess_marrow","pip_marrow","nan_marrow"),
              traits=("historical","corrective"), provenance="genealogy_v0_1"),
    _resident("lark_vessey", "Lark Vessey", age_band="adult", gender="woman",
              household="vessey", occupation="flower seller",
              schedule="flower_seller", kin=("wren_vessey","fen_vessey","bess_bell"),
              traits=("reserved","kind"), role_bound=True,
              provenance="genealogy_v0_1"),
    _resident("wren_vessey", "Wren Vessey", age_band="child", gender="girl",
              household="vessey", occupation="schoolchild", schedule="child_school",
              kin=("lark_vessey","fen_vessey","bess_bell"),
              traits=("generous","curious"), provenance="genealogy_v0_1"),
    _resident("fen_vessey", "Uncle Fen Vessey", age_band="older", gender="man",
              household="vessey", occupation="gardener", schedule="gardener",
              kin=("lark_vessey","wren_vessey","bess_bell"),
              traits=("territorial","patient"), provenance="genealogy_v0_1"),
    _resident("bess_bell", "Bess Bell", age_band="adult", gender="woman",
              household="bell", occupation="healer assistant", schedule="healer",
              kin=("mother_bell","young_tam_bell","lark_vessey","fen_vessey"),
              traits=("steady","private"), provenance="genealogy_v0_1"),
    _resident("garr_thorne", "Garr Thorne", age_band="older", gender="man",
              household="thorne", occupation="smith", schedule="smith",
              kin=("cobb_thorne","little_garr_thorne"),
              traits=("industrious","proud"), role_bound=True,
              provenance="genealogy_v0_1"),
    _resident("cobb_thorne", "Cobb Thorne", age_band="adult", gender="man",
              household="thorne", occupation="journeyman smith", schedule="smith",
              kin=("garr_thorne","little_garr_thorne"),
              traits=("precise","quiet"), role_bound=True,
              provenance="genealogy_v0_1"),
    _resident("little_garr_thorne", "Little Garr Thorne", age_band="young_adult",
              gender="man", household="thorne", occupation="smith assistant",
              schedule="smith", kin=("garr_thorne","cobb_thorne"),
              traits=("strong","good_humored"), provenance="genealogy_v0_1"),
    _resident("mother_bell", "Mother Bell", age_band="older", gender="woman",
              household="bell", occupation="herbwife", schedule="healer",
              kin=("bess_bell","young_tam_bell"),
              traits=("practical","devout"), role_bound=True,
              provenance="genealogy_v0_1"),
    _resident("young_tam_bell", "Young Tam Bell", age_band="child", gender="boy",
              household="bell", occupation="schoolchild", schedule="child_school",
              kin=("mother_bell","bess_bell"),
              traits=("curious","collector"), provenance="genealogy_v0_1"),
    _resident("silas_crowe", "Silas Crowe", age_band="adult", gender="man",
              household="crowe", occupation="hunter", schedule="hunter",
              kin=("mara_crowe","young_jory_crowe"),
              traits=("watchful","secretive"), faction="hunters",
              provenance="genealogy_v0_1"),
    _resident("mara_crowe", "Mara Crowe", age_band="adult", gender="woman",
              household="crowe", occupation="trapper and bookkeeper",
              schedule="hunter", kin=("silas_crowe","young_jory_crowe"),
              traits=("sharp","sociable"), provenance="genealogy_v0_1"),
    _resident("young_jory_crowe", "Young Jory Crowe", age_band="teen", gender="boy",
              household="crowe", occupation="hunter apprentice", schedule="hunter",
              kin=("silas_crowe","mara_crowe"),
              traits=("nervous","curious"), faction="hunters",
              provenance="genealogy_v0_1"),
    _resident("tam_rook", "Tam Rook", age_band="elder", gender="man",
              household="rook", occupation="well keeper", schedule="well_keeper",
              traits=("historical","forgetful"), provenance="genealogy_v0_1"),

    # Project-original residents fill the launch-scale social fabric without
    # rewriting any established household or authored major character.
    _resident("marta_kovacs", "Marta Kovács", age_band="adult", gender="woman",
              household="kovacs", occupation="schoolteacher",
              schedule="schoolteacher", traits=("patient","bookish")),
    _resident("otto_kessler", "Otto Kessler", age_band="adult", gender="man",
              household="kessler", occupation="butcher", schedule="butcher",
              traits=("plainspoken","methodical"), role_bound=True),
    _resident("rada_petrescu", "Rada Petrescu", age_band="young_adult",
              gender="woman", household="petrescu", occupation="butcher assistant",
              schedule="butcher_assistant", traits=("ambitious","practical")),
    _resident("petru_ionescu", "Petru Ionescu", age_band="adult", gender="man",
              household="ionescu", occupation="farmer", schedule="farmer",
              kin=("ana_ionescu",), traits=("industrious","quiet")),
    _resident("ana_ionescu", "Ana Ionescu", age_band="adult", gender="woman",
              household="ionescu", occupation="farmer", schedule="farm_household",
              kin=("petru_ionescu",), traits=("sociable","practical")),
    _resident("miklos_farkas", "Miklós Farkas", age_band="adult", gender="man",
              household="farkas", occupation="lamplighter", schedule="lamplighter",
              traits=("night_owl","observant")),
    _resident("elias_dorn", "Elias Dorn", age_band="older", gender="man",
              household="dorn", occupation="recluse", schedule="recluse",
              traits=("private","mechanical")),
    _resident("ilona_szabo", "Ilona Szabó", age_band="adult", gender="woman",
              household="szabo", occupation="chronicler", schedule="chronicler",
              traits=("curious","precise"), faction="Chronicler"),
    _resident("klara_weiss", "Klara Weiss", age_band="adult", gender="woman",
              household="weiss", occupation="seamstress", schedule="seamstress",
              traits=("observant","theatrical")),
    _resident("pavel_orban", "Pavel Orbán", age_band="adult", gender="man",
              household="orban", occupation="carpenter", schedule="carpenter",
              traits=("patient","skeptical"), role_bound=True),
    _resident("milena_varga", "Milena Varga", age_band="adult", gender="woman",
              household="varga", occupation="midwife", schedule="midwife",
              traits=("calm","discreet")),
    _resident("sorin_dragomir", "Sorin Dragomir", age_band="adult", gender="man",
              household="dragomir", occupation="night watchman",
              schedule="night_watch", traits=("vigilant","superstitious"),
)


RESIDENT_BY_ID = {resident["stable_id"]: resident for resident in RESIDENTS}

FACT_POOL = (
    # Ordinary human irregularities dominate.
    {"id":"writes_poetry","class":"ordinary","text":"writes poetry privately and dislikes being praised for it","claim":"reusable","limit":None},
    {"id":"stage_magic","class":"ordinary","text":"has an embarrassing enthusiasm for stage magic","claim":"reusable","limit":None},
    {"id":"stole_sweets","class":"ordinary","text":"stole sweets from a market stall as a child and never admitted it","claim":"reusable","limit":None},
    {"id":"hates_thunder","class":"ordinary","text":"dislikes thunderstorms enough to count the seconds between flashes","claim":"reusable","limit":None},
    {"id":"keeps_newspapers","class":"ordinary","text":"keeps old foreign newspapers tied in bundles under the bed","claim":"reusable","limit":None},
    {"id":"secret_dancer","class":"ordinary","text":"is a very good dancer and pretends not to know how","claim":"limited","limit":4},
    {"id":"bad_singer","class":"ordinary","text":"sings loudly when alone and very badly","claim":"reusable","limit":None},
    {"id":"old_boxing","class":"ordinary","text":"boxed for money once and still knows how to wrap a hand","claim":"limited","limit":3},
    {"id":"keeps_bees","class":"ordinary","text":"keeps a small hidden hive and talks to the bees","claim":"limited","limit":5},
    {"id":"grave_sketches","class":"ordinary","text":"sketches old grave markers for the lettering","claim":"limited","limit":4},
    {"id":"forged_receipt","class":"serious","text":"once forged a receipt to hide a family debt","claim":"limited","limit":2},
    {"id":"illegal_still","class":"serious","text":"is hiding an illegal still beneath the house","claim":"unique","limit":1},
    {"id":"smuggler_past","class":"serious","text":"once carried contraband through the pass for money","claim":"limited","limit":2},
    {"id":"false_testimony","class":"serious","text":"gave false testimony years ago to protect a relative","claim":"limited","limit":2},
    {"id":"hidden_letters","class":"serious","text":"keeps a packet of letters from someone the family refuses to name","claim":"limited","limit":3},
    # Gothic truths are intentionally rare and individually claimable.
    {"id":"vampire_grandmother","class":"gothic","text":"has a grandmother who apparently has not aged in sixty years and lives behind a locked cellar door","claim":"unique","limit":1},
    {"id":"werewolf","class":"gothic","text":"changes into a wolf under conditions they carefully refuse to discuss","claim":"unique","limit":1},
    {"id":"mirror_absent","class":"gothic","text":"has not appeared in a household mirror since last winter","claim":"unique","limit":1},
    {"id":"dead_correspondent","class":"gothic","text":"receives one letter each month in the handwriting of a person buried years ago","claim":"unique","limit":1},
)

FACT_BY_ID = {fact["id"]: fact for fact in FACT_POOL}


def schedule_block(resident, hour, day=None):
    """Pure schedule lookup used by production and offline simulation."""
    schedule_id = resident.get("schedule_id")
    # Game day 1 is Sunday in the current village calendar. Children and the
    # schoolteacher do not report to ordinary lessons on Sundays.
    if (
        day is not None
        and (int(day) - 1) % 7 == 0
        and schedule_id in {"child_school", "schoolteacher"}
    ):
        return {
            "start": 0,
            "end": 24,
            "desired_location": resident["home_id"],
            "activity": "keeps Sunday away from ordinary lessons",
        }
    blocks = SCHEDULES.get(schedule_id) or ()
    for start, end, location, activity in blocks:
        if int(start) <= int(hour) < int(end):
            logical = resident["home_id"] if location == "home" else location
            return {
                "start": int(start),
                "end": int(end),
                "desired_location": logical,
                "activity": activity,
            }
    return {
        "start": 0,
        "end": 24,
        "desired_location": resident["home_id"],
        "activity": "keeps ordinary household hours",
    }


def location_available(location_id, availability):
    state = (availability or {}).get(location_id)
    if state is None:
        return True
    if isinstance(state, bool):
        return state
    return bool(state.get("available", True))


def resolve_schedule(
    resident,
    hour,
    availability=None,
    current_location=None,
    day=None,
):
    """Resolve one hour without replaying skipped time.

    The return value is consequential state only. No ambient action is
    generated here. If a desired location is unavailable, home is the first
    fallback, then the current valid location, then the generic Offstage sink.
    """
    block = schedule_block(resident, hour, day=day)
    desired = block["desired_location"]
    if location_available(desired, availability):
        return {
            **block,
            "logical_location": desired,
            "source": "schedule",
            "reason": None,
        }

    reason_state = (availability or {}).get(desired) or {}
    if isinstance(reason_state, dict):
        why = reason_state.get("reason") or f"{desired}_unavailable"
    else:
        why = f"{desired}_unavailable"

    home = resident["home_id"]
    if location_available(home, availability):
        fallback = home
    elif current_location and location_available(current_location, availability):
        fallback = current_location
    else:
        fallback = "offstage"

    return {
        **block,
        "logical_location": fallback,
        "source": "fallback",
        "reason": why,
    }


def projection_for(location_id):
    if location_id.startswith("home:"):
        return "Offstage"
    return LOCATION_PROJECTIONS.get(location_id, "Offstage")
