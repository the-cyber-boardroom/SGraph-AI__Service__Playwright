# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Playwright__Stack__List
# Response wrapper for Playwright__Stack__Service.list_stacks. host_url on the
# envelope so a serialised response records which host the listing came from.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe
from osbot_utils.type_safe.primitives.domains.web.safe_str.Safe_Str__Url             import Safe_Str__Url

from sgraph_ai_service_playwright__cli.playwright.collections.List__Schema__Playwright__Stack__Info import List__Schema__Playwright__Stack__Info


class Schema__Playwright__Stack__List(Type_Safe):
    host_url : Safe_Str__Url
    stacks   : List__Schema__Playwright__Stack__Info
