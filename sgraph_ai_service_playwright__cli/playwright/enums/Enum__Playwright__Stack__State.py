# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Playwright__Stack__State
# EC2 instance lifecycle state for an ephemeral Playwright stack. Mapped from
# the boto3 instance state-name. Mirrors the vnc section's state vocabulary.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Playwright__Stack__State(str, Enum):
    PENDING     = 'pending'                                                      # EC2 launch accepted, instance not yet running
    RUNNING     = 'running'                                                      # Instance is running; containers may not be up yet
    READY       = 'ready'                                                        # /health/status probe returned 2xx
    TERMINATING = 'terminating'                                                  # shutting-down or stopping
    TERMINATED  = 'terminated'                                                   # stopped or terminated
    UNKNOWN     = 'unknown'                                                      # unmapped boto3 state

    def __str__(self):
        return self.value
