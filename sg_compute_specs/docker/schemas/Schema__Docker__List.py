# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: Schema__Docker__List
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region

from sg_compute_specs.docker.collections.List__Schema__Docker__Info                 import List__Schema__Docker__Info


class Schema__Docker__List(Type_Safe):
    region       : Safe_Str__AWS__Region
    stacks       : List__Schema__Docker__Info
    total        : int = 0
