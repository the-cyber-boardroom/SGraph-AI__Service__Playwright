# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Elastic__Health__Check
# Ordered list of health-check rows. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.elastic.schemas.Schema__Elastic__Health__Check import Schema__Elastic__Health__Check


class List__Schema__Elastic__Health__Check(Type_Safe__List):
    expected_type = Schema__Elastic__Health__Check
