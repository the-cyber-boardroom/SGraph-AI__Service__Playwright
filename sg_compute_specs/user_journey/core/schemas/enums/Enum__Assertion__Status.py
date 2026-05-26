# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Enum__Assertion__Status (per-assertion outcome)
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Assertion__Status(str, Enum):                                           # Per-assertion outcome
    PASSED  = "passed"
    FAILED  = "failed"
    ERROR   = "error"                                                               # could not evaluate (bad input / missing source)
    SKIPPED = "skipped"                                                             # type not evaluated in this context

    def __str__(self): return self.value
