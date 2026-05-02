# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Node__Delete__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe


class Schema__Node__Delete__Response(Type_Safe):
    node_id : str  = ''
    deleted : bool = False
    message : str  = ''
