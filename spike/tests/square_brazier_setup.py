"""QA-only initial conditions for universal Square warming project.

The previous GDD T-13 cancellation was already independently checked.
Reuse the Smith's legitimately retained physical bundle and the real day-four
woodpile. Keep both players in the Square for ordinary telnet interaction.
Do not alter project action state or create test-only virtual firewood.
"""
from evennia.accounts.models import AccountDB
from evennia.scripts.models import ScriptDB
from evennia.utils import search
from world import civic_commissions
from world.community_hearth import FIREWOOD_KEY


def one(key):
    hits = [o for o in search.search_object(key) if o.key == key]
    assert len(hits) == 1, (key, len(hits))
    return hits[0]


assert not any(account.is_connected for account in AccountDB.objects.all())
clock = ScriptDB.objects.get(db_key="village_time")
assert int(clock.db.day or 1) == 4
square = one("Village Square")
tavern = one("The Blood of the Vine")
brazier = one("a public warming brazier")
smith = one("SmithTester")
merchant = one("MerchantTester")
assert brazier.location == square
assert smith.location == square
assert merchant.move_to(square, quiet=True)
commission = civic_commissions.refresh(tavern.db.civic_commission, 4)["commission"]
assert commission and commission["status"] == "cancelled"
bundles = [
    o for o in smith.contents
    if o.key == FIREWOOD_KEY and o.db.civic_firewood is True
]
assert len(bundles) == 1, bundles
assert isinstance(bundles[0].db.gather_event_id, int)
assert not (brazier.db.square_brazier or {}).get("history")
smith.db.qa_brazier_bundle_id = bundles[0].id
smith.db.warmth = 0.25
smith.db.warmth_band = "cold"
print("SQUARE_BRAZIER_REAL_CANCELED_BUNDLE_QA_READY")
