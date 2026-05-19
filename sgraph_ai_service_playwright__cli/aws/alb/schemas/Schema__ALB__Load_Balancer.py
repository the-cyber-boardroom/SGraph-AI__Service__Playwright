# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Schema__ALB__Load_Balancer
# Schema for an ALB load balancer resource.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.alb.collections.Dict__ALB__Tag        import Dict__ALB__Tag
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__LB_Scheme        import Enum__ALB__LB_Scheme
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__LB_State         import Enum__ALB__LB_State
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__LB_Arn  import Safe_Str__ALB__LB_Arn
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__LB_Name import Safe_Str__ALB__LB_Name


class Schema__ALB__Load_Balancer(Type_Safe):
    lb_arn       : Safe_Str__ALB__LB_Arn
    lb_name      : Safe_Str__ALB__LB_Name
    dns_name     : str                  = ''
    state        : Enum__ALB__LB_State  = Enum__ALB__LB_State.UNKNOWN
    scheme       : Enum__ALB__LB_Scheme = Enum__ALB__LB_Scheme.UNKNOWN
    vpc_id       : str                  = ''
    created_time : str                  = ''
    tags         : Dict__ALB__Tag
