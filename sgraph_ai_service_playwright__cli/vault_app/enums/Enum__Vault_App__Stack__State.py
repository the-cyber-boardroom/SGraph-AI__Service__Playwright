# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Vault_App__Stack__State
# Lifecycle state for an ephemeral vault-app EC2 stack. READY means the
# sg-send-vault health endpoint is returning 200. Mirrors sister sections.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Vault_App__Stack__State(str, Enum):
    PENDING     = 'pending'                                                         # EC2 run_instances accepted; instance not yet running
    RUNNING     = 'running'                                                         # EC2 running; containers may still be pulling / booting
    READY       = 'ready'                                                           # sg-send-vault /info/health returns 200
    TERMINATING = 'terminating'                                                     # Terminate initiated; EC2 shutting-down
    TERMINATED  = 'terminated'                                                      # EC2 terminated
    UNKNOWN     = 'unknown'                                                         # Anything AWS returns we don't model

    def __str__(self):
        return self.value
