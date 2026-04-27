# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Pipeline__Run
# Ordered list of journal records, consumed by
# Inventory__HTTP__Client.bulk_post_with_id when the tracker writes a batch.
# Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.elastic.lets.runs.schemas.Schema__Pipeline__Run import Schema__Pipeline__Run


class List__Schema__Pipeline__Run(Type_Safe__List):
    expected_type = Schema__Pipeline__Run
