# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Playwright__Health
# Health snapshot returned by `sp playwright health <name>` and the matching
# FastAPI route. EC2 model: `playwright_ok` is True iff the
# /health/status endpoint on the running instance returned 2xx.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text    import Safe_Str__Text

from sgraph_ai_service_playwright__cli.playwright.enums.Enum__Playwright__Stack__State import Enum__Playwright__Stack__State
from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__Playwright__Stack__Name import Safe_Str__Playwright__Stack__Name


class Schema__Playwright__Health(Type_Safe):
    stack_name    : Safe_Str__Playwright__Stack__Name
    state         : Enum__Playwright__Stack__State = Enum__Playwright__Stack__State.UNKNOWN
    playwright_ok : bool                           = False                       # /health/status returned 2xx
    error         : Safe_Str__Text                                               # Set when instance not found or probe failed; empty otherwise
