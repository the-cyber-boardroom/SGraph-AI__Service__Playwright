# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Stack__Component__Delete__Result
# Ordered list of per-component delete outcomes for one stack.
# Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.observability.schemas.Schema__Stack__Component__Delete__Result import Schema__Stack__Component__Delete__Result


class List__Stack__Component__Delete__Result(Type_Safe__List):
    expected_type = Schema__Stack__Component__Delete__Result
