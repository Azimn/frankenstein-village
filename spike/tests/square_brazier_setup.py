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
# T-13 begins at day-four hour 21, but the real Evennia clock keeps
# ticking during authenticated play and multiple process restarts. Accept
# the elapsed hours instead of rewinding the canonical clock. The brazier
# expiry proof derives its deadline from the actual signed ignition hour.
assert 21 <= int(clock.db.hour) <= 23, (
    "Expected a forward-moving day-four clock after T-13",
    clock.db.hour,
)
square = one("Village Square")
tavern = one("The Blood of the Vine")
brazier = one("a public warming brazier")
smith = one("SmithTester")
merchant = one("MerchantTester")
assert brazier.location == square
# Offline/unpuppeted characters may return to an OOC room at logout.
# Stage the existing player and retained physical bundle for the real
# authenticated Square actions; do not manufacture project resources.
if smith.location != square:
    assert smith.move_to(square, quiet=True)
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
# Fail at the source boundary with an inspectable receipt mismatch, before
# the authenticated playthrough. Never manufacture or rewrite signed evidence.
from world import square_brazier
bundle = bundles[0]
source = ScriptDB.objects.get(db_key="world_event_ledger").get_event(
    bundle.db.gather_event_id
)
if not square_brazier._verified_gather(bundle):
    actor = source.get("actor") if isinstance(source, dict) else None
    payload = source.get("payload") if isinstance(source, dict) else None
    consequence = source.get("consequence") if isinstance(source, dict) else None
    def typed(part):
        return {
            key: (repr(value), type(value).__name__)
            for key, value in (part.items() if isinstance(part, dict) else [])
        }
    raise AssertionError({
        "error": "Physical T13 bundle fails canonical gathering provenance",
        "bundle_id": bundle.id,
        "source_day": bundle.db.source_day,
        "gather_event_id": bundle.db.gather_event_id,
        "source_fields": typed(source),
        "actor_fields": typed(actor),
        "payload_fields": typed(payload),
        "consequence_fields": typed(consequence),
        "canonical_verified": False,
    })
assert not (brazier.db.square_brazier or {}).get("history")
smith.db.qa_brazier_bundle_id = bundles[0].id
smith.db.warmth = 0.25
smith.db.warmth_band = "cold"
print("SQUARE_BRAZIER_REAL_CANCELED_BUNDLE_QA_READY")
