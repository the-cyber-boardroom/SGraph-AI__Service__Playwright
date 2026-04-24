# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Elastic__Info
# Ordered list of ephemeral elastic stack info records. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Info        import Schema__Elastic__Info


class List__Schema__Elastic__Info(Type_Safe__List):
    expected_type = Schema__Elastic__Info
