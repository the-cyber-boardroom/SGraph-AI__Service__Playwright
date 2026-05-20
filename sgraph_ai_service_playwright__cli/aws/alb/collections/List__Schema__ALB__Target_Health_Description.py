# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — List__Schema__ALB__Target_Health_Description
# Typed list of ALB target health description schemas.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Target_Health_Description import Schema__ALB__Target_Health_Description


class List__Schema__ALB__Target_Health_Description(Type_Safe__List):
    expected_type = Schema__ALB__Target_Health_Description
