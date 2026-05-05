# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Pod__Stop__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.primitives.Safe_Str__Message  import Safe_Str__Message
from sg_compute.primitives.Safe_Str__Pod__Name import Safe_Str__Pod__Name


class Schema__Pod__Stop__Response(Type_Safe):
    name    : Safe_Str__Pod__Name = Safe_Str__Pod__Name()
    stopped : bool                = False
    removed : bool                = False
    error   : Safe_Str__Message   = Safe_Str__Message()
