# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__ECS__Task__Status
# Subset of ECS task statuses returned by the describe-tasks API.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__ECS__Task__Status(str, Enum):
    PROVISIONING  = 'PROVISIONING'
    PENDING       = 'PENDING'
    ACTIVATING    = 'ACTIVATING'
    RUNNING       = 'RUNNING'
    DEACTIVATING  = 'DEACTIVATING'
    STOPPING      = 'STOPPING'
    DEPROVISIONING= 'DEPROVISIONING'
    STOPPED       = 'STOPPED'
    DELETED       = 'DELETED'
    UNKNOWN       = 'UNKNOWN'

    def __str__(self):
        return self.value
