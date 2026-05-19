# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Enum__Instance__State
# EC2 instance lifecycle states as reported by describe_instances.
# Mirrors the vault-publish state enum but is specific to the EC2 platform.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Instance__State(str, Enum):
    RUNNING  = 'running'
    STOPPED  = 'stopped'
    PENDING  = 'pending'
    STOPPING = 'stopping'
    UNKNOWN  = 'unknown'

    def __str__(self):
        return self.value
