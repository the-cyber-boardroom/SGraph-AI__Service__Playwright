# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Node__Delete__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.primitives.Safe_Str__Node__Id                                import Safe_Str__Node__Id
from sg_compute.primitives.Safe_Str__Message                                 import Safe_Str__Message


class Schema__Node__Delete__Response(Type_Safe):
    node_id : Safe_Str__Node__Id = Safe_Str__Node__Id()
    deleted : bool               = False
    message : Safe_Str__Message  = Safe_Str__Message()
