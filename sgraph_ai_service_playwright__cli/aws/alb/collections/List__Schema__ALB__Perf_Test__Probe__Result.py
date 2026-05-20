# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — List__Schema__ALB__Perf_Test__Probe__Result
# Typed list of probe-result records for the perf-test report.
# Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sgraph_ai_service_playwright__cli.aws.alb.schemas.Schema__ALB__Perf_Test__Probe__Result import Schema__ALB__Perf_Test__Probe__Result


class List__Schema__ALB__Perf_Test__Probe__Result(Type_Safe__List):
    expected_type = Schema__ALB__Perf_Test__Probe__Result
