# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Step__Status
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Step__Status(str, Enum):                                                # Per-step outcome
    PENDING = "pending"
    RUNNING = "running"
    PASSED  = "passed"
    FAILED  = "failed"
    SKIPPED = "skipped"                                                             # Skipped due to prior failure with halt_on_error

    def __str__(self): return self.value
