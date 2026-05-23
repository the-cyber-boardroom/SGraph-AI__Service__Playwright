# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Sentinel__Enforcement
# L2's enforcement decision derived from a signal. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe               import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str


class Schema__Sentinel__Enforcement(Type_Safe):
    pass_to_origin : bool      = True
    http_status    : int       = 0                                                  # 0 when passing; 403 / 404 when blocking
    body           : Safe_Str                                                       # '' for drop
