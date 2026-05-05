# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Node__List
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                   import List

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.core.node.schemas.Schema__Node__Info                         import Schema__Node__Info
from sg_compute.primitives.Safe_Str__AWS__Region                             import Safe_Str__AWS__Region
from sg_compute.primitives.Safe_Int__Uptime__Seconds                         import Safe_Int__Uptime__Seconds


class Schema__Node__List(Type_Safe):
    nodes  : List[Schema__Node__Info]
    total  : Safe_Int__Uptime__Seconds = Safe_Int__Uptime__Seconds()    # reuse non-negative int
    region : Safe_Str__AWS__Region     = Safe_Str__AWS__Region()
