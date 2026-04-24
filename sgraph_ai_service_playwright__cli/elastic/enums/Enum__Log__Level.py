# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Log__Level
# Log-level enum for the synthetic log documents produced by
# Synthetic__Data__Generator. Matches common application log levels so the
# resulting dataset shapes like real observability telemetry.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Log__Level(str, Enum):
    DEBUG = 'DEBUG'
    INFO  = 'INFO'
    WARN  = 'WARN'
    ERROR = 'ERROR'

    def __str__(self):
        return self.value
