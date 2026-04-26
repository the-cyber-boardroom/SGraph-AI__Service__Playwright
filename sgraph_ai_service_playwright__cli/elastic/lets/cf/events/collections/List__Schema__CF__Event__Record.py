# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — List__Schema__CF__Event__Record
# Ordered list of parsed CloudFront events. One per .gz line.
# Bulk-posted to sg-cf-events-{YYYY-MM-DD}. Pure type definition.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List               import Type_Safe__List

from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__CF__Event__Record import Schema__CF__Event__Record


class List__Schema__CF__Event__Record(Type_Safe__List):
    expected_type = Schema__CF__Event__Record
