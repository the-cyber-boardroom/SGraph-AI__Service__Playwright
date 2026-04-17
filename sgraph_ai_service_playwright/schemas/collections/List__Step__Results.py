# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — List__Step__Results (spec §6)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List                               import Type_Safe__List

from sgraph_ai_service_playwright.schemas.results.Schema__Step__Result__Base                        import Schema__Step__Result__Base


class List__Step__Results(Type_Safe__List):
    expected_type = Schema__Step__Result__Base
