# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Schema__ALB__TG__Create__Request
# Request schema for creating an ALB target group.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Protocol            import Enum__ALB__Protocol
from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Target_Type         import Enum__ALB__Target_Type
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__TG_Name    import Safe_Str__ALB__TG_Name
from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Health_Check    import Schema__ALB__Health_Check


class Schema__ALB__TG__Create__Request(Type_Safe):
    name         : Safe_Str__ALB__TG_Name
    protocol     : Enum__ALB__Protocol    = Enum__ALB__Protocol.HTTP
    port         : int                    = 8080
    vpc_id       : str                    = ''
    target_type  : Enum__ALB__Target_Type = Enum__ALB__Target_Type.INSTANCE
    health_check : Schema__ALB__Health_Check
    tags         : dict                   = None
