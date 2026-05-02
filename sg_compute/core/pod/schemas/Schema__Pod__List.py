# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Pod__List
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                   import List

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute.core.pod.schemas.Schema__Pod__Info                           import Schema__Pod__Info


class Schema__Pod__List(Type_Safe):
    pods : List[Schema__Pod__Info]
