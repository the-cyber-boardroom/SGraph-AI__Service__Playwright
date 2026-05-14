# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Playwright__Stack__Create__Response
# Returned once by `sp playwright create`. Carries the launched pod's
# container id + the host port the Playwright API is reachable on.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text         import Safe_Str__Text

from sgraph_ai_service_playwright__cli.playwright.enums.Enum__Playwright__Stack__State    import Enum__Playwright__Stack__State
from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__Docker__Image  import Safe_Str__Docker__Image
from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__Playwright__Stack__Name import Safe_Str__Playwright__Stack__Name


class Schema__Playwright__Stack__Create__Response(Type_Safe):
    stack_name   : Safe_Str__Playwright__Stack__Name
    pod_name     : Safe_Str__Text                                                   # host-plane pod name (== stack_name)
    container_id : Safe_Str__Text                                                   # docker container id from the host-plane
    image        : Safe_Str__Docker__Image                                          # full image ref launched
    host_port    : int                            = 0                               # host port mapped to the pod's :8000
    started      : bool                           = False
    state        : Enum__Playwright__Stack__State = Enum__Playwright__Stack__State.PENDING
    error        : Safe_Str__Text                                                   # set when the host-plane reported a start failure; empty otherwise
