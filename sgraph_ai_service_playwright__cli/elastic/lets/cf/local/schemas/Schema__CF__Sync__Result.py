# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf local: Schema__CF__Sync__Result
# Outcome of a "download" run: how many objects were fetched, skipped (already
# present), failed, and the total bytes written. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__CF__Sync__Result(Type_Safe):
    downloaded : int  = 0
    skipped    : int  = 0
    failed     : int  = 0
    bytes      : int  = 0
    done       : bool = False
