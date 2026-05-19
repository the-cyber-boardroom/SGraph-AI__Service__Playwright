# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Schema__ALB__Listener
# Schema for an ALB listener resource.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Protocol                import Enum__ALB__Protocol
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__LB_Arn         import Safe_Str__ALB__LB_Arn
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__Listener_Arn   import Safe_Str__ALB__Listener_Arn
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Default_Action      import Schema__ALB__Default_Action


class Schema__ALB__Listener(Type_Safe):
    listener_arn   : Safe_Str__ALB__Listener_Arn
    lb_arn         : Safe_Str__ALB__LB_Arn
    protocol       : Enum__ALB__Protocol     = Enum__ALB__Protocol.HTTP
    port           : int                     = 0
    default_action : Schema__ALB__Default_Action
