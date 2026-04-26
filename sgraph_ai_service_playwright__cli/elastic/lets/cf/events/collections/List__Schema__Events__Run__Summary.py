# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Events__Run__Summary
# Ordered list of run summaries returned by Events__Read.list_runs() and
# rendered by `sp el lets cf events list`. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Run__Summary import Schema__Events__Run__Summary


class List__Schema__Events__Run__Summary(Type_Safe__List):
    expected_type = Schema__Events__Run__Summary
