# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Linux__Info
# Ordered list of Linux stack info entries. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Info            import Schema__Linux__Info


class List__Schema__Linux__Info(Type_Safe__List):
    expected_type = Schema__Linux__Info
