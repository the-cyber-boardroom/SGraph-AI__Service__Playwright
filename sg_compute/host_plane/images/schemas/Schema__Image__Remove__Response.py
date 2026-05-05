# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Image__Remove__Response
# Result of DELETE /images/{name}.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Image__Remove__Response(Type_Safe):
    name    : str  = ''
    removed : bool = False
    error   : str  = ''
