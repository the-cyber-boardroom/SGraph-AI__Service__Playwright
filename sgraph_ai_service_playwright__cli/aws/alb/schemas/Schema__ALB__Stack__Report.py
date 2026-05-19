# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Schema__ALB__Stack__Report
# Result report returned from ALB__Stack__Provisioner create/delete operations.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Schema__AWS__Phase__Result import List__Schema__AWS__Phase__Result
from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Str                        import List__Str


class Schema__ALB__Stack__Report(Type_Safe):
    operation       : str                         = ''
    stack_name      : str                         = ''
    ok              : bool                        = False
    total_ms        : int                         = 0
    lb_arn          : str                         = ''
    lb_dns_name     : str                         = ''
    tg_arn          : str                         = ''
    listener_arn    : str                         = ''
    alb_sg_id       : str                         = ''
    target_sg_id    : str                         = ''
    phases          : List__Schema__AWS__Phase__Result
    error           : str                         = ''
    rollback_errors : List__Str
