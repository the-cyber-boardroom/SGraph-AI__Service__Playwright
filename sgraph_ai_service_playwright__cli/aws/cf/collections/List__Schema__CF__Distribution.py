# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__CF__Distribution
# Ordered list of CloudFront distribution summaries. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.cf.schemas.Schema__CF__Distribution      import Schema__CF__Distribution


class List__Schema__CF__Distribution(Type_Safe__List):
    expected_type = Schema__CF__Distribution
