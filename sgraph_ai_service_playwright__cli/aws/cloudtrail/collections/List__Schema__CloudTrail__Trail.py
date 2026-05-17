# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/cloudtrail — List__Schema__CloudTrail__Trail
# Typed list of CloudTrail trail schemas.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.cloudtrail.schemas.Schema__CloudTrail__Trail import Schema__CloudTrail__Trail


class List__Schema__CloudTrail__Trail(Type_Safe__List):
    expected_type = Schema__CloudTrail__Trail
