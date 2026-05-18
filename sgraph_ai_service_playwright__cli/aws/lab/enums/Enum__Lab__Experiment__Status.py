# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Enum__Lab__Experiment__Status
# Execution lifecycle of a single lab experiment.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Lab__Experiment__Status(str, Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    OK      = 'ok'
    FAILED  = 'failed'
    TIMEOUT = 'timeout'
    ABORTED = 'aborted'
