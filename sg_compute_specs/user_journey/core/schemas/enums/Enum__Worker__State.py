# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Enum__Worker__State (one worker container's state)
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Worker__State(str, Enum):                                               # One worker container's state
    PENDING = "pending"                                                             # queued, not launched
    RUNNING = "running"                                                             # container running the journey
    PASSED  = "passed"                                                              # journey terminal, all assertions passed
    FAILED  = "failed"                                                              # journey terminal, an assertion failed
    ERROR   = "error"                                                               # the run could not complete
    STOPPED = "stopped"                                                             # killed by the conductor / operator

    def __str__(self): return self.value
