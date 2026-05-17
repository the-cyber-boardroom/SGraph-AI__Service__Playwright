# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Lambda__State
# Lambda function deployment state as returned by GetFunction.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Lambda__State(str, Enum):
    ACTIVE   = 'Active'
    INACTIVE = 'Inactive'
    PENDING  = 'Pending'
    FAILED   = 'Failed'

    def __str__(self):
        return self.value
