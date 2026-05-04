# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: Enum__Kibana__Probe__Status
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Kibana__Probe__Status(str, Enum):
    UNREACHABLE   = 'unreachable'
    UPSTREAM_DOWN = 'upstream-down'
    BOOTING       = 'booting'
    READY         = 'ready'
    UNKNOWN       = 'unknown'

    def __str__(self):
        return self.value
