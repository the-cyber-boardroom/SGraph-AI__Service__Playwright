# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Playwright__Health
# Health snapshot returned by `sp playwright health <name>` and the matching
# FastAPI route. POD backend: health is derived from the host-plane pod
# state (running / not) — the running container's own /health/status probe
# is a follow-up once pod reachability from the CLI is wired.
# Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text         import Safe_Str__Text

from sgraph_ai_service_playwright__cli.playwright.enums.Enum__Playwright__Stack__State    import Enum__Playwright__Stack__State
from sgraph_ai_service_playwright__cli.playwright.primitives.Safe_Str__Playwright__Stack__Name import Safe_Str__Playwright__Stack__Name


class Schema__Playwright__Health(Type_Safe):
    stack_name : Safe_Str__Playwright__Stack__Name
    state      : Enum__Playwright__Stack__State = Enum__Playwright__Stack__State.UNKNOWN
    running    : bool                          = False                              # True iff the host-plane reports the pod container up
    error      : Safe_Str__Text                                                     # set when the pod was not found or the host-plane was unreachable
