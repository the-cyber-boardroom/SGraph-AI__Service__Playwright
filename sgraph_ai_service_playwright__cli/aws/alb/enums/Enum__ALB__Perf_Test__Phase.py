# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Enum__ALB__Perf_Test__Phase
# Ordered phases for the ALB perf-test orchestrator. String values double as
# the phase display name in the live renderer and the JSON report.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__ALB__Perf_Test__Phase(str, Enum):
    PROVISION       = 'PROVISION'
    WAIT_LB_ACTIVE  = 'WAIT_LB_ACTIVE'
    REGISTER_TARGET = 'REGISTER_TARGET'
    WAIT_HEALTHY    = 'WAIT_HEALTHY'
    HTTP_PROBE      = 'HTTP_PROBE'
    TEARDOWN        = 'TEARDOWN'

    def __str__(self):
        return self.value
