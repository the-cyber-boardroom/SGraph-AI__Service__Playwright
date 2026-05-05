# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Pod__Stop__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe


class Schema__Pod__Stop__Response(Type_Safe):
    name    : str  = ''
    stopped : bool = False
    removed : bool = False
    error   : str  = ''
