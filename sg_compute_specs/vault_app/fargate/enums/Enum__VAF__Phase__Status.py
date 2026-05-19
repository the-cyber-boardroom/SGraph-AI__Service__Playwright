# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute_specs vault_app/fargate — Enum__VAF__Phase__Status
# Lifecycle states for a single timed phase in the vault-app fargate flow.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__VAF__Phase__Status(str, Enum):
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    OK      = 'OK'
    SKIPPED = 'SKIPPED'
    WARN    = 'WARN'
    ERROR   = 'ERROR'

    def __str__(self):
        return self.value
