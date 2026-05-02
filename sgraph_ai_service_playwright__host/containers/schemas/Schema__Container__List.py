# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Container__List
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                            import Type_Safe
from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List                          import Type_Safe__List

from sgraph_ai_service_playwright__host.containers.schemas.Schema__Container__Info             import Schema__Container__Info


class List__Schema__Container__Info(Type_Safe__List):
    expected_type = Schema__Container__Info


class Schema__Container__List(Type_Safe):
    containers : List__Schema__Container__Info
    count      : int = 0
