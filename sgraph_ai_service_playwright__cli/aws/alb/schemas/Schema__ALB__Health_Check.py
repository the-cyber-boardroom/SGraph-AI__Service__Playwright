# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/alb — Schema__ALB__Health_Check
# Health check configuration for ALB target groups.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__ALB__Health_Check(Type_Safe):
    protocol              : str = 'HTTP'
    port                  : str = '8080'
    path                  : str = '/info/health'
    interval_seconds      : int = 30
    timeout_seconds       : int = 5
    healthy_threshold     : int = 5
    unhealthy_threshold   : int = 2
