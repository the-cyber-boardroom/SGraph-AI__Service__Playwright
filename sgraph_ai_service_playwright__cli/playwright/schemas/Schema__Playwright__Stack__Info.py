# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Playwright__Stack__Info
# Public view of one ephemeral Playwright stack (a pod on a host). Does NOT
# carry the api_key — that is only echoed once on create.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text         import Safe_Str__Text

from sgraph_ai_service_playwright__cli.playwright.enums.Enum__Playwright__Stack__State    import Enum__Playwright__Stack__State
from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__Docker__Image  import Safe_Str__Docker__Image
from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__Playwright__Stack__Name import Safe_Str__Playwright__Stack__Name


class Schema__Playwright__Stack__Info(Type_Safe):
    stack_name : Safe_Str__Playwright__Stack__Name
    pod_name   : Safe_Str__Text                                                     # host-plane pod name (== stack_name)
    image      : Safe_Str__Docker__Image                                            # full image ref the pod runs
    state      : Enum__Playwright__Stack__State = Enum__Playwright__Stack__State.UNKNOWN
    status     : Safe_Str__Text                                                     # raw host-plane status string ("Up 2 hours", "Exited (0)…")
    host_port  : int                            = 0                                 # host port mapped to the pod's :8000
    created_at : Safe_Str__Text                                                     # ISO-8601 from the host-plane
