# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Enum__ALB__LB_Scheme
# ALB load balancer scheme (internet-facing or internal).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__ALB__LB_Scheme(str, Enum):
    INTERNET_FACING = 'internet-facing'
    INTERNAL        = 'internal'
    UNKNOWN         = 'unknown'

    def __str__(self):
        return self.value
