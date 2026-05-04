# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__Pod__List
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                        import Type_Safe
from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List       import Type_Safe__List

from sg_compute.host_plane.pods.schemas.Schema__Pod__Info                   import Schema__Pod__Info


class List__Schema__Pod__Info(Type_Safe__List):
    expected_type = Schema__Pod__Info


class Schema__Pod__List(Type_Safe):
    pods  : List__Schema__Pod__Info
    count : int = 0
