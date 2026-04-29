# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Stack__Type__Catalog__Entry
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.catalog.schemas.Schema__Stack__Type__Catalog__Entry import Schema__Stack__Type__Catalog__Entry


class List__Schema__Stack__Type__Catalog__Entry(Type_Safe__List):
    expected_type = Schema__Stack__Type__Catalog__Entry
