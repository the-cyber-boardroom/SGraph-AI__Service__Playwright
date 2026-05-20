# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Enum__ALB__Target_Type
# ALB target group target type (instance, ip, lambda, alb).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__ALB__Target_Type(str, Enum):
    INSTANCE = 'instance'
    IP       = 'ip'
    LAMBDA   = 'lambda'
    ALB      = 'alb'

    def __str__(self):
        return self.value
