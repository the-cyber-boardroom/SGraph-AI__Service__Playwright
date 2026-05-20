# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Schema__ALB__Perf_Test__Request
# Request schema for the ALB perf-test orchestrator.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.collections.List__Str import List__Str


class Schema__ALB__Perf_Test__Request(Type_Safe):
    vpc_id            : str        = ''
    subnet_ids        : List__Str                                                 # at least 2 in distinct AZs
    target_ip         : str        = ''
    target_port       : int        = 8080
    http_path         : str        = '/info/health'
    expected_status   : int        = 200
    http_probes       : int        = 3
    name              : str        = ''                                            # auto-generated if empty
    keep              : bool       = False
    lb_active_timeout : int        = 360
    healthy_timeout   : int        = 90
    http_timeout      : int        = 30
