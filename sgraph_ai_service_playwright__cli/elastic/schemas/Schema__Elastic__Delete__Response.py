# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Elastic__Delete__Response
# Response for `sp elastic delete NAME`. Empty fields mean the stack was not
# found — the caller maps this to a user-facing "no such stack" message
# (route handlers would map it to 404).
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.identifiers.safe_str.Safe_Str__Id     import Safe_Str__Id

from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id           import List__Instance__Id
from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name


class Schema__Elastic__Delete__Response(Type_Safe):
    stack_name              : Safe_Str__Elastic__Stack__Name
    target                  : Safe_Str__Id                                          # Matches instance id or stack name resolved by service
    terminated_instance_ids : List__Instance__Id
    security_group_deleted  : bool                         = False                  # Best-effort — SG may linger if AWS still reports instance attached
