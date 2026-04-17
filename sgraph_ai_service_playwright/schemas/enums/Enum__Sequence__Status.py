# ═══════════════════════════════════════════════════════════════════════════════
# Playwright Service — Enum__Sequence__Status
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Sequence__Status(str, Enum):                                            # Overall sequence outcome
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"                                                         # All steps passed
    FAILED    = "failed"                                                            # At least one step failed, halt_on_error=True
    PARTIAL   = "partial"                                                           # At least one step failed, halt_on_error=False

    def __str__(self): return self.value
