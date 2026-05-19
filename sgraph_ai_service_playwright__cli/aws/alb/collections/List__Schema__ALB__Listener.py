# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — List__Schema__ALB__Listener
# Typed list of ALB listener schemas.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Listener import Schema__ALB__Listener


class List__Schema__ALB__Listener(Type_Safe__List):
    expected_type = Schema__ALB__Listener
