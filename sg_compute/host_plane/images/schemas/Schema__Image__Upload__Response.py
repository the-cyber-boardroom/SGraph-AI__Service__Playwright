# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Image__Upload__Response
# Result of POST /images/upload (multipart tar upload + docker load).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Image__Upload__Response(Type_Safe):
    loaded     : bool = False
    output     : str  = ''
    error      : str  = ''
    size_bytes : int  = 0
