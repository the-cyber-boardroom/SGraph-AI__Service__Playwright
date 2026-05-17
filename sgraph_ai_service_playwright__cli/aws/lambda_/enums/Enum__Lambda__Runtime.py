# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Lambda__Runtime
# Lambda execution runtimes. Limited to Python versions in active use here.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Lambda__Runtime(str, Enum):
    PYTHON_3_11 = 'python3.11'
    PYTHON_3_12 = 'python3.12'
    PYTHON_3_13 = 'python3.13'

    def __str__(self):
        return self.value
