# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__ACM__Certificate
# Ordered list of ACM certificate records. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.acm.schemas.Schema__ACM__Certificate      import Schema__ACM__Certificate


class List__Schema__ACM__Certificate(Type_Safe__List):
    expected_type = Schema__ACM__Certificate
