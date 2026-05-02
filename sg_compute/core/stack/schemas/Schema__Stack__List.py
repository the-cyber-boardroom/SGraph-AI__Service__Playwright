# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Stack__List
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                   import List

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.core.stack.schemas.Schema__Stack__Info                       import Schema__Stack__Info


class Schema__Stack__List(Type_Safe):
    stacks : List[Schema__Stack__Info]
