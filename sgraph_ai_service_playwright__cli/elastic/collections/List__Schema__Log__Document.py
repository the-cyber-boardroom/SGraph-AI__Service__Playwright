# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Log__Document
# Ordered list of synthetic log documents produced by
# Synthetic__Data__Generator. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Log__Document        import Schema__Log__Document


class List__Schema__Log__Document(Type_Safe__List):
    expected_type = Schema__Log__Document
