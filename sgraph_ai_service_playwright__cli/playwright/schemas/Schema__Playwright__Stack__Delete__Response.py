# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Playwright__Stack__Delete__Response
# Returned by Playwright__Stack__Service.delete_stack. `removed` is False
# when no pod matched the target — caller maps to HTTP 404.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text         import Safe_Str__Text

from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__Playwright__Stack__Name import Safe_Str__Playwright__Stack__Name


class Schema__Playwright__Stack__Delete__Response(Type_Safe):
    stack_name : Safe_Str__Playwright__Stack__Name                                  # resolved logical name; empty on miss
    pod_name   : Safe_Str__Text                                                     # resolved pod name; empty on miss
    removed    : bool                            = False                            # False on miss
