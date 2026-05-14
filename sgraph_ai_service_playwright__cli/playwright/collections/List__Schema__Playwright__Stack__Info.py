# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Playwright__Stack__Info
# Type_Safe__List for the listing response. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.playwright.schemas.Schema__Playwright__Stack__Info import Schema__Playwright__Stack__Info


class List__Schema__Playwright__Stack__Info(Type_Safe__List):
    expected_type = Schema__Playwright__Stack__Info
