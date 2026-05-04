# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: Schema__Elastic__Delete__Response
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id

from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id           import List__Instance__Id
from sg_compute_specs.elastic.primitives.Safe_Str__Elastic__Stack__Name             import Safe_Str__Elastic__Stack__Name


class Schema__Elastic__Delete__Response(Type_Safe):
    stack_name              : Safe_Str__Elastic__Stack__Name
    target                  : Safe_Str__Id
    terminated_instance_ids : List__Instance__Id
    security_group_deleted  : bool = False
