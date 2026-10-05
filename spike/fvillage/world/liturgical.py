"""The liturgical calendar of St. Lazarus Church.

Catholic, explicitly — the old calendar is the village's yearly structure,
and it's already written: Advent, Christmas, Lent, Holy Week, Easter,
Corpus Christi, the patronal feast, All Saints, All Souls. The MUD's
yearly event system gets a massive head start because the Church did the
scheduling centuries ago.

Game day 1 = October 4 (the village opened its eyes on a real October 4).
A game day is 24 game-hours; the calendar maps day counts to month/day.

Each feast carries observances: schedule deviations the routine ticker
applies (Vasile tending the vigil candles on All Souls, not digging),
tavern-fare notes (Lenten Fridays are meatless — Bram complains), and
ledger-worthy happenings.
"""

import datetime

# Game day 1 = this month/day. The village's year tracks the real year's
# shape; only the year number is left unstated (it's always "this year").
EPOCH_MONTH, EPOCH_DAY = 10, 4

# Fixed feasts: (month, day) -> dict. "rank" is solemnity for the bell.
FIXED_FEASTS = {
    (11, 1): {
        "name": "All Saints",
        "rank": "solemnity",
        "note": "The whole court of heaven. The church is full twice over.",
    },
    (11, 2): {
        "name": "All Souls",
        "rank": "solemnity",
        "note": "Every name is read. Vasile digs nothing this week — he tends.",
        "observance": "all_souls",
    },
    (12, 25): {
        "name": "Christmas",
        "rank": "solemnity",
        "note": "Midnight mass. The tavern does a roaring trade after.",
    },
    (1, 6): {
        "name": "Epiphany",
        "rank": "feast",
        "note": "The wise men got lost too, Andrei says. It's allowed.",
    },
    (2, 2): {
        "name": "Candlemas",
        "rank": "feast",
        "note": "Blessing of the candles. The church smells of wax for a week.",
    },
    (6, 24): {
        "name": "Nativity of St. John the Baptist",
        "rank": "solemnity",
        "note": "Midsummer. Bonfires on the square, and Andrei pretends not to see the old customs mixed in.",
    },
    (7, 29): {
        "name": "Sts. Martha, Mary and Lazarus",
        "rank": "patronal",
        "note": "The patronal feast — the village's biggest day. The patron got up and walked; the village celebrates by refusing to sit still.",
        "observance": "patronal",
    },
    (8, 15): {
        "name": "Assumption",
        "rank": "solemnity",
        "note": "The harvest blessing. Bread from the new wheat on the altar.",
    },
    (11, 11): {
        "name": "St. Martin",
        "rank": "feast",
        "note": "The first snow is usually falling. The tavern serves goose, if there's goose.",
    },
}


def easter(year):
    """Gregorian computus. Returns (month, day). Anonymous algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return month, day


def _shift(md, days):
    """Shift a (month, day) by days, ignoring year. Returns (month, day)."""
    base = datetime.date(2000, md[0], md[1]) + datetime.timedelta(days=days)
    return base.month, base.day


def moveable_feasts(year):
    """Easter-dependent feasts for a year. Returns {(m,d): info}."""
    em, ed = easter(year)
    easter_date = datetime.date(year, em, ed)
    out = {}
    out[(em, ed)] = {
        "name": "Easter",
        "rank": "solemnity",
        "note": "He is risen. The bells go mad at dawn and nobody minds.",
    }
    ash = _shift((em, ed), -46)
    out[ash] = {
        "name": "Ash Wednesday",
        "rank": "feria",
        "note": "Dust thou art. The tavern goes meatless on Fridays till Easter — Bram complains for forty days.",
        "observance": "lent",
    }
    good = _shift((em, ed), -2)
    out[good] = {
        "name": "Good Friday",
        "rank": "solemnity",
        "note": "The church is bare. No bell from Thursday night till the vigil.",
        "observance": "triduum",
    }
    corpus = _shift((em, ed), 60)
    out[corpus] = {
        "name": "Corpus Christi",
        "rank": "solemnity",
        "note": "Procession through the square. The whole village turns out, even the ones who won't say why.",
    }
    return out


def advent_sunday(year):
    """First Sunday of Advent: Sunday nearest Nov 30."""
    nov30 = datetime.date(year, 11, 30)
    # Sunday is weekday 6 in Python's Monday=0; find nearest Sunday
    offset = (6 - nov30.weekday()) % 7
    if offset > 3:
        offset -= 7
    return (nov30 + datetime.timedelta(days=offset)).month, (
        nov30 + datetime.timedelta(days=offset)
    ).day


def game_date(game_day, epoch=(EPOCH_MONTH, EPOCH_DAY)):
    """Map a game day-count to (month, day). Day 1 = epoch."""
    base = datetime.date(2000, epoch[0], epoch[1])
    d = base + datetime.timedelta(days=game_day - 1)
    return d.month, d.day


def is_sunday(game_day):
    """Day 1 was a Sunday (Oct 4). The village keeps the Lord's day."""
    return (game_day - 1) % 7 == 0


def weekday_name(game_day):
    return ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday"][(game_day - 1) % 7]


def feast_on(month, day, year=2000):
    """Feast info for a month/day, or None. Checks fixed, moveable, Advent."""
    if (month, day) in FIXED_FEASTS:
        return dict(FIXED_FEASTS[(month, day)])
    for (m, d), info in moveable_feasts(year).items():
        if (m, d) == (month, day):
            return dict(info)
    am, ad = advent_sunday(year)
    if (month, day) == (am, ad):
        return {
            "name": "First Sunday of Advent",
            "rank": "solemnity",
            "note": "The new year begins in the dark. Four candles, one lit.",
        }
    return None


def next_feast(game_day, limit=370):
    """Next feast at or after this game day. Returns (in_days, info)."""
    for ahead in range(limit):
        m, d = game_date(game_day + ahead)
        info = feast_on(m, d)
        if info:
            return ahead, info
    return None, None


def is_lent(month, day, year=2000):
    """True if the date falls in Lent (Ash Wednesday..Holy Saturday)."""
    em, ed = easter(year)
    ash = datetime.date(year, *_shift((em, ed), -46))
    holy_sat = datetime.date(year, *_shift((em, ed), -1))
    cur = datetime.date(year, month, day)
    # handle year wrap for early-January dates vs December Easter math
    return ash <= cur <= holy_sat


# --- Ember days and Rogation days (the 1890 directory's quarterly rhythm) ---
# Ember days: Wed/Fri/Sat after (1) First Sunday of Lent, (2) Pentecost,
# (3) Holy Cross (Sep 14), (4) St. Lucy (Dec 13). Days of fast and
# ordination — the village eats plain and Andrei is busy.
# Rogation days: Mon-Wed before Ascension Thursday (Easter + 39).
# Procession days; the fields get blessed.


def ember_days(year):
    """Return set of (month, day) Ember days for the year."""
    em, ed = easter(year)
    easter_d = datetime.date(year, em, ed)
    anchors = [
        easter_d - datetime.timedelta(days=46 - 7),  # ~1st Sun of Lent
        easter_d + datetime.timedelta(days=7),  # Pentecost
        datetime.date(year, 9, 14),  # Holy Cross
        datetime.date(year, 12, 13),  # St. Lucy
    ]
    days = set()
    for anchor in anchors:
        # next Wednesday after anchor
        wd = anchor.weekday()  # Mon=0
        wed = anchor + datetime.timedelta(days=(2 - wd) % 7 or 7)
        for off in (0, 2, 3):  # Wed, Fri, Sat
            d = wed + datetime.timedelta(days=off)
            days.add((d.month, d.day))
    return days


def rogation_days(year):
    """Return set of (month, day) Rogation days for the year."""
    em, ed = easter(year)
    ascension = datetime.date(year, em, ed) + datetime.timedelta(days=39)
    days = set()
    for d in (3, 2, 1):
        r = ascension - datetime.timedelta(days=d)
        days.add((r.month, r.day))
    return days


def is_ember_day(month, day, year=2000):
    return (month, day) in ember_days(year)


def is_rogation_day(month, day, year=2000):
    return (month, day) in rogation_days(year)
# Each returns a list of (regular_key, room_key, reason) deviations.


def observance_deviations(observance):
    if observance == "all_souls":
        return [
            ("vasile", "St. Lazarus Church", "tends the vigil candles; digs nothing this week"),
            ("andrei", "St. Lazarus Church", "reads every name"),
            ("magda", "St. Lazarus Church", "brought the altar linen herself"),
        ]
    if observance == "patronal":
        return [
            ("vasile", "Village Square", "the patronal feast — even the dead get the day off"),
            ("andrei", "Village Square", "blesses the bonfire"),
            ("magda", "Village Square", "ran the feast linen and won't hear otherwise"),
            ("janos", "Village Square", "the Hound takes the feast day like everyone else"),
        ]
    if observance == "lent":
        return []  # fare change only, handled in tavern prose later
    if observance == "triduum":
        return [
            ("andrei", "St. Lazarus Church", "the church is bare and he doesn't leave it"),
        ]
    return []
