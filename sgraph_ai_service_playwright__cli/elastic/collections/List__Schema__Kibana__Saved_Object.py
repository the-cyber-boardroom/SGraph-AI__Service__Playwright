# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Kibana__Saved_Object
# Ordered list of Kibana saved-object records returned by _find. Pure type def.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Kibana__Saved_Object import Schema__Kibana__Saved_Object


class List__Schema__Kibana__Saved_Object(Type_Safe__List):
    expected_type = Schema__Kibana__Saved_Object
