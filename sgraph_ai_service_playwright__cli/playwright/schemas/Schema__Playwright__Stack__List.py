# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Playwright__Stack__List
# Response wrapper for Playwright__Stack__Service.list_stacks. `region` on the
# envelope so a serialised response records which AWS region the listing came
# from. Mirrors Schema__Vnc__Stack__List.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                             import Type_Safe

from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region import Safe_Str__AWS__Region
from sgraph_ai_service_playwright__cli.playwright.collections.List__Schema__Playwright__Stack__Info import List__Schema__Playwright__Stack__Info


class Schema__Playwright__Stack__List(Type_Safe):
    region : Safe_Str__AWS__Region
    stacks : List__Schema__Playwright__Stack__Info
