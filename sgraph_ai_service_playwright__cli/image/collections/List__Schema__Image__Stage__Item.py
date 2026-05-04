# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Image__Stage__Item
# Ordered list of files / trees to stage into the Docker build context.
# Order matters: items are copied sequentially; later items can overwrite
# earlier ones (deliberate — supports a "base tree + targeted overrides"
# pattern). Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.image.schemas.Schema__Image__Stage__Item     import Schema__Image__Stage__Item


class List__Schema__Image__Stage__Item(Type_Safe__List):
    expected_type = Schema__Image__Stage__Item
