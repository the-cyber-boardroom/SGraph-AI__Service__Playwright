# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__CF__Origin
# Ordered list of CloudFront origin entries. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.cf.schemas.Schema__CF__Origin             import Schema__CF__Origin


class List__Schema__CF__Origin(Type_Safe__List):
    expected_type = Schema__CF__Origin
