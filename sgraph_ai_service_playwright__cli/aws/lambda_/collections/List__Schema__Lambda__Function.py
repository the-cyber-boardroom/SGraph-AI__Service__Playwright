# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__Lambda__Function
# Ordered list of Lambda function summaries. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.lambda_.schemas.Schema__Lambda__Function import Schema__Lambda__Function


class List__Schema__Lambda__Function(Type_Safe__List):
    expected_type = Schema__Lambda__Function
