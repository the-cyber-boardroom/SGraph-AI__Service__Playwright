# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Node__Create__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.core.node.schemas.Schema__Node__Info                         import Schema__Node__Info
from sg_compute.primitives.Safe_Str__Message                                 import Safe_Str__Message


class Schema__Node__Create__Response(Type_Safe):
    node   : Schema__Node__Info
    status : Safe_Str__Message = Safe_Str__Message()
