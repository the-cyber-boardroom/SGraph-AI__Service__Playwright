# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Node__List
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                   import List

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.core.node.schemas.Schema__Node__Info                         import Schema__Node__Info


class Schema__Node__List(Type_Safe):
    nodes : List[Schema__Node__Info]
