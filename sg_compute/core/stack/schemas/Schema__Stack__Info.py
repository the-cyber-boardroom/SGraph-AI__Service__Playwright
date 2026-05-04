# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Schema__Stack__Info  (multi-node stack; placeholder for phase 2+)
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                   import List

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe


class Schema__Stack__Info(Type_Safe):
    stack_id  : str       = ''
    spec_ids  : List[str]
    node_ids  : List[str]
    status    : str       = ''
