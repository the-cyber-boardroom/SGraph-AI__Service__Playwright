# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Schema__ALB__Perf_Test__Report
# Result report returned from ALB__Perf_Test__Runner.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Schema__AWS__Phase__Result      import List__Schema__AWS__Phase__Result
from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Str                              import List__Str
from sgraph_ai_service_playwright__cli.aws.alb.collections.List__Schema__ALB__Perf_Test__Probe__Result import List__Schema__ALB__Perf_Test__Probe__Result


class Schema__ALB__Perf_Test__Report(Type_Safe):
    operation         : str                                                  = 'perf-test'
    stack_name        : str                                                  = ''
    ok                : bool                                                 = False
    total_ms          : int                                                  = 0
    lb_arn            : str                                                  = ''
    lb_dns_name       : str                                                  = ''
    tg_arn            : str                                                  = ''
    target_registered : bool                                                 = False
    probes            : List__Schema__ALB__Perf_Test__Probe__Result
    phases            : List__Schema__AWS__Phase__Result
    error             : str                                                  = ''
    rollback_errors   : List__Str
