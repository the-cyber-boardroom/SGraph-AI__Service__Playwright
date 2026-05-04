# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Pod__Info
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.primitives.enums.Enum__Pod__State                            import Enum__Pod__State


class Schema__Pod__Info(Type_Safe):
    pod_name    : str             = ''
    node_id     : str             = ''
    image       : str             = ''
    state       : Enum__Pod__State = Enum__Pod__State.PENDING
    ports       : str             = ''
