# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Schema__ALB__Target_Health_Description
# Health description for a single registered target.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.alb.enums.Enum__ALB__Target_Health import Enum__ALB__Target_Health


class Schema__ALB__Target_Health_Description(Type_Safe):
    target_id     : str                      = ''
    target_port   : int                      = 0
    health_status : Enum__ALB__Target_Health = Enum__ALB__Target_Health.UNKNOWN
    reason_code   : str                      = ''
    description   : str                      = ''
