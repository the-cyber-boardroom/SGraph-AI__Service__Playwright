# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Schema__Local_Claude__Delete__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Local_Claude__Delete__Response(Type_Safe):
    stack_name  : str  = ''
    deleted     : bool = False
    message     : str  = ''
    elapsed_ms  : int  = 0
