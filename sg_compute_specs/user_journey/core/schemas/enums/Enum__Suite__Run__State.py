# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Enum__Suite__Run__State (a suite run's lifecycle state)
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Suite__Run__State(str, Enum):                                           # A suite run's lifecycle state
    PENDING = "pending"                                                             # accepted, no workers launched yet
    RUNNING = "running"                                                             # at least one worker in flight
    DONE    = "done"                                                                # all workers terminal, none failed
    FAILED  = "failed"                                                              # all workers terminal, some failed
    STOPPED = "stopped"                                                             # operator-stopped before completion

    def __str__(self): return self.value
