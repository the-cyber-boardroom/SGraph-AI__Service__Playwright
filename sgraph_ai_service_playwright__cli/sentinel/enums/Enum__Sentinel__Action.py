# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Sentinel__Action
# The action L2 enforces for a verdict. pass = forward to origin; drop_403 /
# deflect_404 = block with the named HTTP status (addendum GAP 6.1).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Sentinel__Action(str, Enum):
    PASS        = 'pass'
    DROP_403    = 'drop_403'
    DEFLECT_404 = 'deflect_404'
