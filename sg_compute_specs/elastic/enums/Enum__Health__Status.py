# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Elastic: Enum__Health__Status
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Health__Status(str, Enum):
    OK   = 'ok'
    WARN = 'warn'
    FAIL = 'fail'
    SKIP = 'skip'

    def __str__(self):
        return self.value
