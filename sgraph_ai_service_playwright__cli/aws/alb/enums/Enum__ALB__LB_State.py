# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Enum__ALB__LB_State
# ALB load balancer lifecycle states as reported by the AWS API.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__ALB__LB_State(str, Enum):
    ACTIVE          = 'active'
    PROVISIONING    = 'provisioning'
    ACTIVE_IMPAIRED = 'active_impaired'
    FAILED          = 'failed'
    UNKNOWN         = 'unknown'

    def __str__(self):
        return self.value
