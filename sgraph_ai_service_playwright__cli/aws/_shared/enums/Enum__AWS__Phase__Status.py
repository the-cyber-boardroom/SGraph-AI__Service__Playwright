# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/_shared — Enum__AWS__Phase__Status
# Lifecycle states for a single timed phase in any aws/* provisioning flow.
# Mirrors Enum__VAF__Phase__Status (vault_app/fargate) so the renderer can be
# shared; v0.2.34 keeps both copies — deduplicate in a later Librarian pass.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__AWS__Phase__Status(str, Enum):
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    OK      = 'OK'
    SKIPPED = 'SKIPPED'
    WARN    = 'WARN'
    ERROR   = 'ERROR'

    def __str__(self):
        return self.value
