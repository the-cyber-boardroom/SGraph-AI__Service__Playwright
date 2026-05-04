# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Container__Start__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__Container__Start__Response(Type_Safe):
    name       : str
    container_id: str
    started    : bool = False
    error      : str
