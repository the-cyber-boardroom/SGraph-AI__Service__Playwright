# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI observe — Schema__Observe__Source__Status
# Status record for a single observability source adapter.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Observe__Source__Status(Type_Safe):
    name         : str  = ''
    connected    : bool = False
    stream_count : int  = 0
    last_event   : str  = ''
