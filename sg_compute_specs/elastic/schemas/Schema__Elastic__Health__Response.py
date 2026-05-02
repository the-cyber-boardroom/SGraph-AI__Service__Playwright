# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: Schema__Elastic__Health__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.elastic.collections.List__Schema__Elastic__Health__Check      import List__Schema__Elastic__Health__Check
from sg_compute_specs.elastic.primitives.Safe_Str__Elastic__Stack__Name             import Safe_Str__Elastic__Stack__Name


class Schema__Elastic__Health__Response(Type_Safe):
    stack_name : Safe_Str__Elastic__Stack__Name
    all_ok     : bool                           = False
    checks     : List__Schema__Elastic__Health__Check
