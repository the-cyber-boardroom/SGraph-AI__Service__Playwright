# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Stack__Summary__List
# Response wrapper for GET /catalog/stacks.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.catalog.collections.List__Schema__Stack__Summary import List__Schema__Stack__Summary


class Schema__Stack__Summary__List(Type_Safe):
    stacks : List__Schema__Stack__Summary
