# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Schema__ALB__Target_Group
# Schema for an ALB target group resource.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.alb.collections.Dict__ALB__Tag          import Dict__ALB__Tag
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Protocol            import Enum__ALB__Protocol
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Target_Type         import Enum__ALB__Target_Type
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__TG_Arn     import Safe_Str__ALB__TG_Arn
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__TG_Name    import Safe_Str__ALB__TG_Name


class Schema__ALB__Target_Group(Type_Safe):
    tg_arn                 : Safe_Str__ALB__TG_Arn
    tg_name                : Safe_Str__ALB__TG_Name
    protocol               : Enum__ALB__Protocol   = Enum__ALB__Protocol.HTTP
    port                   : int                   = 0
    vpc_id                 : str                   = ''
    target_type            : Enum__ALB__Target_Type = Enum__ALB__Target_Type.INSTANCE
    health_check_protocol  : str                   = ''
    health_check_port      : str                   = ''
    health_check_path      : str                   = ''
    tags                   : Dict__ALB__Tag
