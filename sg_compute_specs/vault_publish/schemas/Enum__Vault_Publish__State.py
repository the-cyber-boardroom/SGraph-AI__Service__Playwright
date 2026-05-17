# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Enum__Vault_Publish__State
# Observed lifecycle state of a published vault-app stack.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Vault_Publish__State(str, Enum):
    RUNNING  = 'running'
    STOPPED  = 'stopped'
    PENDING  = 'pending'
    STOPPING = 'stopping'
    UNKNOWN  = 'unknown'

    def __str__(self):
        return self.value
