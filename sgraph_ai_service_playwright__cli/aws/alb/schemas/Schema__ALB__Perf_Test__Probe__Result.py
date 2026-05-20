# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Schema__ALB__Perf_Test__Probe__Result
# One HTTP-probe attempt during a perf-test run.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__ALB__Perf_Test__Probe__Result(Type_Safe):
    attempt     : int = 0
    status_code : int = 0
    duration_ms : int = 0
    body_size   : int = 0
    error       : str = ''
