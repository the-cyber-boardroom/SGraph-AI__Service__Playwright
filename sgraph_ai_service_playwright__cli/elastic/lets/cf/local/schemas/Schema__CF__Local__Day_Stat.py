# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf local: Schema__CF__Local__Day_Stat
# Per-day rollup of the local raw-cf-logs cache. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__CF__Local__Day_Stat(Type_Safe):
    day        : str                                                                 # YYYY/MM/DD
    files      : int = 0
    bytes      : int = 0
    hours      : int = 0                                                             # distinct hour partitions present
