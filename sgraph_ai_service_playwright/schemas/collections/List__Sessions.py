# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — List__Sessions (spec §6)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List                               import Type_Safe__List

from sgraph_ai_service_playwright.schemas.session.Schema__Session__Info                             import Schema__Session__Info


class List__Sessions(Type_Safe__List):
    expected_type = Schema__Session__Info
