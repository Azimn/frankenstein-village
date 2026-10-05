"""The liturgical calendar of St. Lazarus Church.

Catholic, explicitly — the old calendar is the village's yearly structure,
and it's already written. Source: *The Official Catholic Directory for the
Year of Our Lord 1890* (P.J. Kenedy, New York), full text via the Internet
Archive (archive.org/details/officialcatholic1890unse). The Sunday ordo —
every Sunday's name and Gospel — is transcribed from that book's calendar;
see world/data/ordo-1890.json for the extraction. Gaps from OCR noise were
filled from the Tridentine lectionary, which the book follows exactly
(verified against its legible entries).

The village keeps the 1890 ordo on its own epoch: game day 1 (Oct 4) is the
Twentieth Sunday after Pentecost, matching the book's late-October position
(the book's 23rd Sunday after Pentecost falls Oct 26, 1890). The Sunday
sequence cycles by Sunday-count, so the temporal year is always internally
consistent; movable feasts anchor to the lectionary Easter of the current
cycle. Fixed feasts keep their real calendar dates.

Each feast carries observances: schedule deviations the routine ticker
applies (Vasile tending the vigil candles on All Souls, not digging),
tavern-fare notes (Lenten Fridays are meatless — Bram complains), and
ledger-worthy happenings.
"""

import datetime

# Game day 1 = this month/day. Day 1 was a Sunday.
EPOCH_MONTH, EPOCH_DAY = 10, 4

# The 1890 ordo, in sequence: (season, n, sunday_name, gospel_ref,
# gospel_topic, homily). Day 1 = index 0 = 20th Sunday after Pentecost.
# Gospel references/topics transcribed from the 1890 Directory; homilies
# are Father Andrei's voice on each text.
SUNDAY_ORDO = [
    ("pentecost", 20, "Twentieth Sunday after Pentecost",
     "St. John iv. 46-53", "Healing of the Son of the Ruler of Capharnaum",
     "'Unless you see signs you will not believe' — and He healed the boy anyway, from a distance. Faith at a distance counts."),
    ("pentecost", 21, "Twenty-first Sunday after Pentecost",
     "St. Matt. xviii. 23-35", "The Unforgiving Servant",
     "Forgiven a fortune, he throttled a man for pennies. We are all that servant. Forgive as you have been forgiven, or the arithmetic finds you."),
    ("pentecost", 22, "Twenty-second Sunday after Pentecost",
     "St. Matt. xxii. 15-21", "The Coin of Tribute",
     "Render unto Caesar. The coin bears Caesar's face; you bear God's. Give each what is stamped with his image."),
    ("pentecost", 23, "Twenty-third Sunday after Pentecost",
     "St. Matt. ix. 18-26", "The Ruler's Daughter",
     "'The maid is not dead, but sleepeth.' I say this over every grave I stand beside. Sleep. Not death. Sleep."),
    ("pentecost", 24, "Twenty-fourth Sunday after Pentecost",
     "St. Matt. xiii. 24-30", "The Parable of the Cockle",
     "Let wheat and weeds grow together till harvest. It is not your job to pull weeds — you'd tear the wheat. Leave the sorting to the harvest."),
    ("pentecost", 25, "Twenty-fifth Sunday after Pentecost",
     "St. Matt. xiii. 31-35", "The Mustard Seed and the Leaven",
     "The kingdom is a mustard seed, is leaven in the dough. Small, hidden, unstoppable. Do not despise small beginnings."),
    ("pentecost", 26, "Twenty-sixth and Last Sunday after Pentecost",
     "St. Matt. xxiv. 15-35", "The Abomination of Desolation",
     "The last Sunday speaks of the end. 'Heaven and earth shall pass away, but my words shall not pass away.' Hold the rope. That is all."),
    ("advent", 1, "First Sunday of Advent",
     "St. Luke xxi. 25-33", "Signs Foretelling the End",
     "Advent begins with the end of the world. The Church is not subtle: stay awake. The night is for watching."),
    ("advent", 2, "Second Sunday of Advent",
     "St. Matt. xi. 2-10", "John Sends His Disciples to Christ",
     "'Art thou he that is to come?' Even John, in prison, asked. Ask from your prison. He answered with evidence, not rebuke."),
    ("advent", 3, "Third Sunday of Advent",
     "St. John i. 19-28", "John Bears Witness of Christ",
     "'I am not the Christ.' John knew who he wasn't. Half of holiness is knowing what you are not."),
    ("advent", 4, "Fourth Sunday of Advent",
     "St. Luke iii. 1-16", "John's Mission and Preaching",
     "'Prepare ye the way.' The way is prepared by straight paths — no crooked dealing, no rough edge left unexamined."),
    ("christmas", 0, "Sunday in the Octave of Christmas",
     "St. Luke ii. 33-40", "The Prophecy of Simeon",
     "Simeon waited his whole life for one moment in the temple. 'Now thou dost dismiss thy servant in peace.' Some prayers take a lifetime. Pray them anyway."),
    ("epiphany", 1, "First Sunday after the Epiphany",
     "St. Luke ii. 42-52", "Jesus Found Amongst the Doctors",
     "He was twelve, and stayed behind asking questions. Ask yours. The temple can take it."),
    ("epiphany", 2, "Second Sunday after the Epiphany",
     "St. John ii. 1-11", "The Marriage of Cana",
     "The first miracle was wine at a wedding, not thunder on a mountain. Joy is not frivolous. It is the first sign."),
    ("epiphany", 3, "Third Sunday after the Epiphany",
     "St. Matt. viii. 1-13", "Christ Heals the Centurion's Servant",
     "A soldier asked, and would not presume to host. 'Only say the word.' Some prayers are short because they are certain."),
    ("lent", 1, "First Sunday of Lent",
     "St. Matt. iv. 1-11", "Jesus Is Tempted by the Devil",
     "Forty days, and the devil brought Scripture. Not every voice quoting holy words is holy. Test them."),
    ("lent", 2, "Second Sunday of Lent",
     "St. Matt. xvii. 1-9", "Transfiguration of Our Lord",
     "They saw Him shining and wanted to build tents and stay. We don't get to stay on the mountain. We get to remember it."),
    ("lent", 3, "Third Sunday of Lent",
     "St. Luke xi. 14-28", "Jesus Casts Out a Devil",
     "A house swept clean and empty invites seven worse tenants. Fill the clean rooms — with work, with prayer, with each other."),
    ("lent", 4, "Fourth Sunday of Lent",
     "St. John vi. 1-15", "The Miracle of the Loaves and Fishes",
     "Five loaves. He did not conjure bread from nothing; He multiplied what a boy brought. Bring what you have."),
    ("lent", 5, "Passion Sunday",
     "St. John viii. 46-59", "The Jews Try to Stone Jesus",
     "The truth nearly got Him killed before it got Him killed. Say it anyway. Gently, if you can."),
    ("lent", 6, "Palm Sunday",
     "St. Matt. xxvi. and xxvii.", "The Passion of Our Lord",
     "They shouted Hosanna on Sunday. By Friday — well. You know the story. Examine your own shouting."),
    ("easter", 0, "Easter Sunday",
     "St. Mark xvi. 1-7", "The Resurrection",
     "She went to anoint a corpse and found an empty tomb. Grief is not the end of the story. It never was."),
    ("easter", 1, "First Sunday after Easter",
     "St. John xx. 19-31", "Jesus Appears to His Disciples",
     "Thomas needed to touch the wounds. Christ let him. Doubt is not the opposite of faith — it is faith asking for hands."),
    ("easter", 2, "Second Sunday after Easter",
     "St. John x. 11-16", "The Good Shepherd",
     "The hired hand runs. The shepherd stays. Know which one you are to the people who count on you."),
    ("easter", 3, "Third Sunday after Easter",
     "St. John xvi. 16-22", "Joy after Sorrow",
     "'A little while, and you shall not see me.' Sorrow has a clock on it. It does not feel like it. It does."),
    ("easter", 4, "Fourth Sunday after Easter",
     "St. John xvi. 5-14", "Christ Promises the Comforter",
     "He said it was better for Him to go. Absence making room for presence — I think of that every time I hold this rope."),
    ("easter", 5, "Fifth Sunday after Easter",
     "St. John xvi. 23-30", "Ask and It Shall Be Granted",
     "Ask in His name. The name is not a password. It is a direction — ask as He would ask."),
    ("ascension", 0, "Sunday after the Ascension",
     "St. John xv. 26-xvi. 4", "The Spirit Shall Testify",
     "They stood staring at the sky, and were told to stop. Heaven is not up. It is forward. Go back to the work."),
    ("whit", 0, "Pentecost",
     "St. John xiv. 23-31", "Descent of the Holy Ghost",
     "Tongues of fire, and everyone heard in their own language. The Spirit translates. If they cannot understand you, the problem may be yours."),
    ("pentecost", 1, "Trinity Sunday",
     "St. Matt. xxviii. 18-20", "The Disciples Commissioned to Preach",
     "Go and teach all nations. Not some. The commission has no borders, which is inconvenient for all of us."),
    ("pentecost", 2, "Second Sunday after Pentecost",
     "St. Luke xiv. 16-24", "The Parable of the Supper",
     "The invited made excuses — a field, oxen, a wife. All reasonable. That is what makes them dangerous."),
    ("pentecost", 3, "Third Sunday after Pentecost",
     "St. Luke xv. 1-10", "The Parable of the Lost Sheep",
     "Ninety-nine safe, and He goes after the one. Arithmetic is not love. Thank God."),
    ("pentecost", 4, "Fourth Sunday after Pentecost",
     "St. Luke v. 1-11", "The Miraculous Draught of Fishes",
     "They fished all night and caught nothing. Then at His word, the nets broke. Obedience first, understanding later."),
    ("pentecost", 5, "Fifth Sunday after Pentecost",
     "St. Matt. v. 20-24", "The Justice of the Pharisees",
     "'Unless your justice exceeds...' Not abolished — exceeded. The bar is higher than the rulebook, not lower."),
    ("pentecost", 6, "Sixth Sunday after Pentecost",
     "St. Mark viii. 1-9", "Jesus Feeds the Multitude",
     "Seven loaves, a few fishes, four thousand fed. Again with the boy's lunch. Heaven multiplies; it does not conjure."),
    ("pentecost", 7, "Seventh Sunday after Pentecost",
     "St. Matt. vii. 15-21", "The False Prophets",
     "By their fruits you shall know them. Not their words, not their robes — their fruits. Look at what grows around a person."),
    ("pentecost", 8, "Eighth Sunday after Pentecost",
     "St. Luke xvi. 1-9", "The Parable of the Unjust Steward",
     "The steward was commended for shrewdness, not honesty. A hard parable. Perhaps: use the world's tools for heaven's work, and be naive about neither."),
    ("pentecost", 9, "Ninth Sunday after Pentecost",
     "St. Luke xix. 41-47", "Jesus Weeps over Jerusalem",
     "He wept over the city. Not in anger — in grief. If you love this village, you will weep for it too. That is allowed."),
    ("pentecost", 10, "Tenth Sunday after Pentecost",
     "St. Luke xviii. 9-14", "The Pharisee and the Publican",
     "The Pharisee listed his virtues; the publican beat his breast. One went home justified. It was not the one with the list."),
    ("pentecost", 11, "Eleventh Sunday after Pentecost",
     "St. Mark vii. 31-37", "Jesus Cures the Deaf and Dumb",
     "'Ephpheta — be opened.' Some of us need our ears opened more than our mouths."),
    ("pentecost", 12, "Twelfth Sunday after Pentecost",
     "St. Luke x. 23-37", "The Good Samaritan",
     "The priest passed by. The Levite passed by. I think of that every time I put on this stole. Do not be the priest in the parable."),
    ("pentecost", 13, "Thirteenth Sunday after Pentecost",
     "St. Luke xvii. 11-19", "The Cure of the Ten Lepers",
     "Ten cleansed, one returned. Nine were healed and kept walking. Gratitude is the difference between cured and whole."),
    ("pentecost", 14, "Fourteenth Sunday after Pentecost",
     "St. Matt. vi. 24-33", "The Mammon of Iniquity",
     "No man can serve two masters. You know which one you serve by where your worry lives."),
    ("pentecost", 15, "Fifteenth Sunday after Pentecost",
     "St. Luke vii. 11-16", "The Widow of Naim",
     "He stopped a funeral for a widow's only son. No one asked Him to. Mercy does not wait to be asked."),
    ("pentecost", 16, "Sixteenth Sunday after Pentecost",
     "St. Luke xiv. 1-11", "Christ Heals the Dropsical Man",
     "He healed on the Sabbath and they watched to accuse Him. Do good on the wrong day if you must. The day will forgive you."),
    ("pentecost", 17, "Seventeenth Sunday after Pentecost",
     "St. Matt. xxii. 35-46", "The First and Greatest Commandment",
     "Love God, love your neighbor. Everything else is commentary. If your theology makes you worse at this, burn the theology."),
    ("pentecost", 18, "Eighteenth Sunday after Pentecost",
     "St. Matt. ix. 1-8", "Jesus Cures the Man Sick of the Palsy",
     "'Thy sins are forgiven thee' — before the legs, the soul. We carry people to Him on stretchers. That is what intercession is."),
    ("pentecost", 19, "Nineteenth Sunday after Pentecost",
     "St. Matt. xxii. 1-14", "The Parable of the Marriage Feast",
     "Many are called, few chosen — and one was thrown out for no wedding garment. Come as you are, but come dressed for the feast."),
]

ORDO_LEN = len(SUNDAY_ORDO)
EASTER_ORDO_INDEX = next(
    i for i, e in enumerate(SUNDAY_ORDO) if e[0] == "easter" and e[1] == 0
)


def sunday_index(game_day):
    """0-based count of Sundays since day 1."""
    return (game_day - 1) // 7


def sunday_ordo(game_day):
    """The 1890 ordo entry for this game day's Sunday.

    Returns (season, n, sunday_name, gospel_ref, gospel_topic, homily).
    For non-Sundays, returns the coming Sunday's entry.
    """
    idx = sunday_index(game_day) % ORDO_LEN
    return SUNDAY_ORDO[idx]


def easter_gameday(game_day):
    """Game day of Easter Sunday for the ordo cycle containing game_day."""
    si = sunday_index(game_day)
    cycle_start = (si // ORDO_LEN) * ORDO_LEN
    return 1 + (cycle_start + EASTER_ORDO_INDEX) * 7


# Fixed feasts: (month, day) -> dict. "rank" is solemnity for the bell.
# Dates verified against the 1890 Directory's calendar. July 29: the 1890
# calendar keeps St. Martha, Virgin alone — no Lazarus. The village keeps
# Lazarus anyway, by old local custom; the note says so honestly.
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
        "name": "St. Martha, Virgin",
        "rank": "patronal",
        "note": "Rome keeps Martha alone on this day — but this village has always kept Lazarus too, by old custom. The patronal feast: the patron got up and walked, so the village refuses to sit still.",
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


def _moveable_feasts_gameday(game_day):
    """Easter-anchored feasts for the ordo cycle containing game_day.

    Returns {game_day: info}. Offsets from the lectionary Easter, so the
    movable feasts always agree with the Sunday ordo.
    """
    e = easter_gameday(game_day)
    return {
        e: {
            "name": "Easter",
            "rank": "solemnity",
            "note": "He is risen. The bells go mad at dawn and nobody minds.",
        },
        e - 46: {
            "name": "Ash Wednesday",
            "rank": "feria",
            "note": "Dust thou art. The tavern goes meatless on Fridays till Easter — Bram complains for forty days.",
            "observance": "lent",
        },
        e - 2: {
            "name": "Good Friday",
            "rank": "solemnity",
            "note": "The church is bare. No bell from Thursday night till the vigil.",
            "observance": "triduum",
        },
        e + 39: {
            "name": "Ascension",
            "rank": "solemnity",
            "note": "He was lifted up. The village looks at the sky for a week.",
        },
        e + 49: {
            "name": "Pentecost",
            "rank": "solemnity",
            "note": "Tongues of fire. The church is full and loud.",
        },
        e + 60: {
            "name": "Corpus Christi",
            "rank": "solemnity",
            "note": "Procession through the square. The whole village turns out, even the ones who won't say why.",
        },
    }


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


def feast_on(month, day):
    """Fixed-feast info for a month/day, or None."""
    if (month, day) in FIXED_FEASTS:
        return dict(FIXED_FEASTS[(month, day)])
    return None


def feast_on_gameday(game_day):
    """Full feast info (fixed + movable) for a game day, or None."""
    m, d = game_date(game_day)
    info = feast_on(m, d)
    if info:
        return info
    return _moveable_feasts_gameday(game_day).get(game_day)


def next_feast(game_day, limit=400):
    """Next feast at or after this game day. Returns (in_days, info)."""
    for ahead in range(limit):
        info = feast_on_gameday(game_day + ahead)
        if info:
            return ahead, info
    return None, None


def is_lent(game_day):
    """True if the game day falls in Lent (Ash Wed..Holy Saturday)."""
    e = easter_gameday(game_day)
    return (e - 46) <= game_day <= (e - 1)


# --- Ember days and Rogation days (the 1890 directory's quarterly rhythm) ---
# Ember days: Wed/Fri/Sat after (1) First Sunday of Lent, (2) Pentecost,
# (3) Holy Cross (Sep 14), (4) St. Lucy (Dec 13). Days of fast and
# ordination — the village eats plain and Andrei is busy.
# Rogation days: Mon-Wed before Ascension Thursday (Easter + 39).
# Procession days; the fields get blessed.
# Anchored to the lectionary Easter of the current ordo cycle.


def _ember_gamedays(game_day):
    e = easter_gameday(game_day)
    first_lent_sunday = e - 42
    pentecost = e + 49
    # Holy Cross and St. Lucy by month/day -> nearest game day in cycle
    out = set()
    for anchor in (first_lent_sunday, pentecost):
        # Wednesday after anchor (anchor is always a Sunday)
        wed = anchor + 3
        out.update((wed, wed + 2, wed + 3))
    # fixed-date anchors: find the game day with that month/day in range
    for (m, d) in ((9, 14), (12, 13)):
        for g in range(game_day - 200, game_day + 200):
            if g > 0 and game_date(g) == (m, d):
                # Wednesday after the following Sunday
                wd = (g - 1) % 7  # 0=Sunday
                sunday = g - wd
                wed = sunday + 3
                out.update((wed, wed + 2, wed + 3))
                break
    return out


def is_ember_day(game_day):
    return game_day in _ember_gamedays(game_day)


def is_rogation_day(game_day):
    e = easter_gameday(game_day)
    ascension = e + 39
    return game_day in (ascension - 3, ascension - 2, ascension - 1)
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
