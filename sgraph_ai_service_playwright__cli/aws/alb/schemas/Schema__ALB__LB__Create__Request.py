# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Schema__ALB__LB__Create__Request
# Request schema for creating an ALB load balancer.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Str    import List__Str
from sgraph_ai_service_playwright__cli.aws.alb.collections.Dict__ALB__Tag   import Dict__ALB__Tag
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__LB_Scheme        import Enum__ALB__LB_Scheme
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__LB_Name import Safe_Str__ALB__LB_Name


class Schema__ALB__LB__Create__Request(Type_Safe):
    name            : Safe_Str__ALB__LB_Name
    subnets         : List__Str                                              # list of subnet IDs
    security_groups : List__Str
    scheme          : Enum__ALB__LB_Scheme = Enum__ALB__LB_Scheme.INTERNET_FACING
    tags            : Dict__ALB__Tag
