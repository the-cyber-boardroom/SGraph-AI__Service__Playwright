# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Schema__ALB__Listener__Create__Request
# Request schema for creating an ALB listener.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Protocol          import Enum__ALB__Protocol
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__LB_Arn   import Safe_Str__ALB__LB_Arn
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__TG_Arn   import Safe_Str__ALB__TG_Arn


class Schema__ALB__Listener__Create__Request(Type_Safe):
    lb_arn          : Safe_Str__ALB__LB_Arn
    protocol        : Enum__ALB__Protocol = Enum__ALB__Protocol.HTTP
    port            : int                 = 80
    default_tg_arn  : Safe_Str__ALB__TG_Arn
