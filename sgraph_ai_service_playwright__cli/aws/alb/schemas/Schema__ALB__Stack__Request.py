# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Schema__ALB__Stack__Request
# Request schema for provisioning a full ALB stack.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Str    import List__Str
from sgraph_ai_service_playwright__cli.aws.alb.collections.Dict__ALB__Tag   import Dict__ALB__Tag
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Target_Type import Enum__ALB__Target_Type


class Schema__ALB__Stack__Request(Type_Safe):
    stack_name         : str                    = ''
    vpc_id             : str                    = ''
    subnet_ids         : List__Str                                          # exactly 2 subnets for internet-facing ALB
    target_type        : Enum__ALB__Target_Type = Enum__ALB__Target_Type.INSTANCE
    lb_port            : int                    = 80
    target_port        : int                    = 8080
    health_check_path  : str                    = '/info/health'
    tags               : Dict__ALB__Tag
