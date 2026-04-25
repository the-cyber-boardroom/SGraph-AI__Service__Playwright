# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Inventory__Run__Summary
# Ordered list of run summaries returned by Inventory__Read.list() and
# rendered by `sp el lets cf inventory list`. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__Inventory__Run__Summary import Schema__Inventory__Run__Summary


class List__Schema__Inventory__Run__Summary(Type_Safe__List):
    expected_type = Schema__Inventory__Run__Summary
