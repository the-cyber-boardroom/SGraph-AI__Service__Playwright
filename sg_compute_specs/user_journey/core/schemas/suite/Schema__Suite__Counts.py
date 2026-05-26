# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Suite__Counts (worker tallies for a suite run)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                       import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_UInt       import Safe_UInt


class Schema__Suite__Counts(Type_Safe):                                             # Worker tallies (all default 0)
    pending : Safe_UInt
    running : Safe_UInt
    passed  : Safe_UInt
    failed  : Safe_UInt
    error   : Safe_UInt
