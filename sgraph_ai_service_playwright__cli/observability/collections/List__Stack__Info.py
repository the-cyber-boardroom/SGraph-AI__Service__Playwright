# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Stack__Info
# Ordered list of stacks returned by Observability__Service.list_stacks().
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Info    import Schema__Stack__Info


class List__Stack__Info(Type_Safe__List):
    expected_type = Schema__Stack__Info
