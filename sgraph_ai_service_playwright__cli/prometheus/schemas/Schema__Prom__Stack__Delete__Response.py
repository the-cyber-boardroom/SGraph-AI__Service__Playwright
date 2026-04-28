# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Prom__Stack__Delete__Response
# Returned by Prometheus__Service.delete_stack. All fields empty when no stack
# matched the target — caller maps to HTTP 404. Mirrors
# Schema__OS__Stack__Delete__Response.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id           import List__Instance__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id        import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.prometheus.primitives.Safe_Str__Prom__Stack__Name import Safe_Str__Prom__Stack__Name


class Schema__Prom__Stack__Delete__Response(Type_Safe):
    target                  : Safe_Str__Instance__Id                                # Resolved instance id; empty on miss
    stack_name              : Safe_Str__Prom__Stack__Name                           # Resolved logical name; empty on miss
    terminated_instance_ids : List__Instance__Id                                    # Empty list on miss
