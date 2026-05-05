# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Image__List
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                        import Type_Safe
from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List       import Type_Safe__List

from sg_compute.host_plane.images.schemas.Schema__Image__Info               import Schema__Image__Info


class List__Schema__Image__Info(Type_Safe__List):
    expected_type = Schema__Image__Info


class Schema__Image__List(Type_Safe):
    images : List__Schema__Image__Info
    count  : int = 0
