# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Linux__Stack__State
# Lifecycle states for an ephemeral Linux EC2 stack. Mirrors
# Enum__OS__Stack__State but drops READY (there is no HTTP probe for a plain
# Linux instance — SSM registration is sufficient to declare it operational).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Linux__Stack__State(str, Enum):
    PENDING     = 'pending'                                                         # EC2 run_instances accepted, instance not yet running
    RUNNING     = 'running'                                                         # Instance running + SSM agent registered
    STOPPING    = 'stopping'
    STOPPED     = 'stopped'
    TERMINATING = 'terminating'
    TERMINATED  = 'terminated'
    UNKNOWN     = 'unknown'

    def __str__(self):
        return self.value
