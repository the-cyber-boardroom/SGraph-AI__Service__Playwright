# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — List__Schema__ALB__Load_Balancer
# Typed list of ALB load balancer schemas.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Load_Balancer import Schema__ALB__Load_Balancer


class List__Schema__ALB__Load_Balancer(Type_Safe__List):
    expected_type = Schema__ALB__Load_Balancer
