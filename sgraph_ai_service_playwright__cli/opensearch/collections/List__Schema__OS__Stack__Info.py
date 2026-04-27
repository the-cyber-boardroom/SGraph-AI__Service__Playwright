# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__OS__Stack__Info
# Ordered list of OpenSearch stack infos returned by OpenSearch__Service.list_stacks.
# Pure type definition; mirrors List__Schema__Elastic__Info.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Info   import Schema__OS__Stack__Info


class List__Schema__OS__Stack__Info(Type_Safe__List):
    expected_type = Schema__OS__Stack__Info
