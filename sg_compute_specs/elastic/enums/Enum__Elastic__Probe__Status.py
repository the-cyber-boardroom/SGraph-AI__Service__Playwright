# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: Enum__Elastic__Probe__Status
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Elastic__Probe__Status(str, Enum):
    UNREACHABLE   = 'unreachable'
    AUTH_REQUIRED = 'auth-required'
    RED           = 'red'
    YELLOW        = 'yellow'
    GREEN         = 'green'
    UNKNOWN       = 'unknown'

    def __str__(self):
        return self.value

    def is_ready(self) -> bool:
        return self in (Enum__Elastic__Probe__Status.YELLOW, Enum__Elastic__Probe__Status.GREEN)
