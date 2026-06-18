# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Schema__Content_Proxy__Delete__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe


class Schema__Content_Proxy__Delete__Response(Type_Safe):
    stack_name : str  = ''
    deleted    : bool = False
    message    : str  = ''
    elapsed_ms : int  = 0
