# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Schema__ALB__Stack__Detail
# Describes the current state of a named ALB stack (read-only snapshot).
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__ALB__Stack__Detail(Type_Safe):
    stack_name    : str = ''
    lb_arn        : str = ''
    lb_dns_name   : str = ''
    tg_arn        : str = ''
    listener_arn  : str = ''
    alb_sg_id     : str = ''
    target_sg_id  : str = ''
