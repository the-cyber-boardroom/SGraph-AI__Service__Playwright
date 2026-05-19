# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Enum__VAF__Start__Phase
# Fast-path start phases in execution order.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__VAF__Start__Phase(str, Enum):
    RESOLVE_CONFIG = 'RESOLVE_CONFIG'
    RUN_TASK       = 'RUN_TASK'
    WAIT_RUNNING   = 'WAIT_RUNNING'
    RESOLVE_ENI    = 'RESOLVE_ENI'
    DNS_UPSERT     = 'DNS_UPSERT'
    WAIT_HEALTH    = 'WAIT_HEALTH'

    def __str__(self):
        return self.value
