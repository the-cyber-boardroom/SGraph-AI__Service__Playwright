# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Pod__Info
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.primitives.enums.Enum__Pod__State                            import Enum__Pod__State
from sg_compute.primitives.Safe_Str__Docker__Image                           import Safe_Str__Docker__Image
from sg_compute.primitives.Safe_Str__Message                                 import Safe_Str__Message
from sg_compute.primitives.Safe_Str__Node__Id                                import Safe_Str__Node__Id
from sg_compute.primitives.Safe_Str__Pod__Name                               import Safe_Str__Pod__Name


class Schema__Pod__Info(Type_Safe):
    pod_name    : Safe_Str__Pod__Name   = Safe_Str__Pod__Name()
    node_id     : Safe_Str__Node__Id    = Safe_Str__Node__Id()
    image       : Safe_Str__Docker__Image = Safe_Str__Docker__Image()
    state       : Enum__Pod__State      = Enum__Pod__State.PENDING
    ports       : Safe_Str__Message     = Safe_Str__Message()
