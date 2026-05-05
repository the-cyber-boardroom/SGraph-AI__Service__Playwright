# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Image__Load__Response
# Result of POST /images/load (load from on-host path).
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Image__Load__Response(Type_Safe):
    loaded : bool = False
    output : str  = ''
    error  : str  = ''
