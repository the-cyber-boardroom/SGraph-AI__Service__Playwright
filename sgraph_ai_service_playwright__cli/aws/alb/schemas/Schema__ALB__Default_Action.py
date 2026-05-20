# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Schema__ALB__Default_Action
# Listener default action (forward to target group).
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.alb.primitives.Safe_Str__ALB__TG_Arn import Safe_Str__ALB__TG_Arn


class Schema__ALB__Default_Action(Type_Safe):
    action_type : str             = ''           # e.g. 'forward'
    tg_arn      : Safe_Str__ALB__TG_Arn
