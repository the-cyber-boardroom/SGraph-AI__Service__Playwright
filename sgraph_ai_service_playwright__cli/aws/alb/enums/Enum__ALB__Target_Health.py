# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Enum__ALB__Target_Health
# ALB target health states as reported by describe_target_health.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__ALB__Target_Health(str, Enum):
    INITIAL     = 'initial'
    HEALTHY     = 'healthy'
    UNHEALTHY   = 'unhealthy'
    UNUSED      = 'unused'
    DRAINING    = 'draining'
    UNAVAILABLE = 'unavailable'
    UNKNOWN     = 'unknown'

    def __str__(self):
        return self.value
