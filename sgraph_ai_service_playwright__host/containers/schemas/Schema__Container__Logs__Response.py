# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Container__Logs__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Container__Logs__Response(Type_Safe):
    name  : str
    logs  : str
    tail  : int = 100
