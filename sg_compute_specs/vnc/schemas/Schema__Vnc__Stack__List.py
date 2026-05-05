# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: Schema__Vnc__Stack__List
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region

from sg_compute_specs.vnc.collections.List__Schema__Vnc__Stack__Info                import List__Schema__Vnc__Stack__Info


class Schema__Vnc__Stack__List(Type_Safe):
    region : Safe_Str__AWS__Region
    stacks : List__Schema__Vnc__Stack__Info
