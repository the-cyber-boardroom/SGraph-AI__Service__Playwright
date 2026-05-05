# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Pod__Logs__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.primitives.Safe_Int__Log__Lines  import Safe_Int__Log__Lines
from sg_compute.primitives.Safe_Str__Log__Content import Safe_Str__Log__Content
from sg_compute.primitives.Safe_Str__Pod__Name   import Safe_Str__Pod__Name


class Schema__Pod__Logs__Response(Type_Safe):
    container : Safe_Str__Pod__Name   = Safe_Str__Pod__Name()
    lines     : Safe_Int__Log__Lines  = Safe_Int__Log__Lines()
    content   : Safe_Str__Log__Content = Safe_Str__Log__Content()
    truncated : bool                  = False
