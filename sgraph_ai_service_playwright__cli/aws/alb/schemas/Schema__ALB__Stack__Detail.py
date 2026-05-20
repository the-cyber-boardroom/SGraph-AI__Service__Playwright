# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Schema__ALB__Stack__Detail
# Describes the current state of a named ALB stack (read-only snapshot).
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__LB_Arn        import Safe_Str__ALB__LB_Arn
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__TG_Arn        import Safe_Str__ALB__TG_Arn
from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__Listener_Arn  import Safe_Str__ALB__Listener_Arn


class Schema__ALB__Stack__Detail(Type_Safe):
    stack_name    : str                          = ''
    lb_arn        : Safe_Str__ALB__LB_Arn
    lb_dns_name   : str                          = ''
    tg_arn        : Safe_Str__ALB__TG_Arn
    listener_arn  : Safe_Str__ALB__Listener_Arn
    alb_sg_id     : str                          = ''
    target_sg_id  : str                          = ''
