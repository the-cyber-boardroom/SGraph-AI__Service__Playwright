# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Docker__Info
# Ordered list of Docker stack info entries. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__Info          import Schema__Docker__Info


class List__Schema__Docker__Info(Type_Safe__List):
    expected_type = Schema__Docker__Info
