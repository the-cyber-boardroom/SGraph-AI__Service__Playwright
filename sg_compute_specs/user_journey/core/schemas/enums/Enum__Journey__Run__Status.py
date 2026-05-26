# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Enum__Journey__Run__Status (one worker's terminal verdict)
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Journey__Run__Status(str, Enum):                                        # One journey run's terminal verdict
    PASSED = "passed"                                                               # all assertions passed
    FAILED = "failed"                                                               # at least one assertion failed
    ERROR  = "error"                                                                # the run could not complete

    def __str__(self): return self.value
