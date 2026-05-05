# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Pod__Logs__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe


class Schema__Pod__Logs__Response(Type_Safe):
    container : str  = ''
    lines     : int  = 0
    content   : str  = ''
    truncated : bool = False
