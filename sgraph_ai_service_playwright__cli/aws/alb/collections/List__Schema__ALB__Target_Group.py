# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — List__Schema__ALB__Target_Group
# Typed list of ALB target group schemas.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Target_Group import Schema__ALB__Target_Group


class List__Schema__ALB__Target_Group(Type_Safe__List):
    expected_type = Schema__ALB__Target_Group
