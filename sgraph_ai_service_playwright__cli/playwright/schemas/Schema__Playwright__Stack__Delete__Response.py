# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Playwright__Stack__Delete__Response  (vnc-shaped)
# Returned by Playwright__Stack__Service.delete_stack. Empty `target` and
# empty `terminated_instance_ids` signals a miss — route maps to 404.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.ec2.collections.List__Instance__Id       import List__Instance__Id
from sgraph_ai_service_playwright__cli.ec2.primitives.Safe_Str__Instance__Id    import Safe_Str__Instance__Id
from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__Playwright__Stack__Name import Safe_Str__Playwright__Stack__Name

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe


class Schema__Playwright__Stack__Delete__Response(Type_Safe):
    target                  : Safe_Str__Instance__Id                             # Resolved instance id; empty on miss
    stack_name              : Safe_Str__Playwright__Stack__Name                  # Empty on miss
    terminated_instance_ids : List__Instance__Id                                 # Empty list on miss → route maps to 404
