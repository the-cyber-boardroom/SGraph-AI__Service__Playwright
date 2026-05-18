# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__IAM__Audit__Severity
# Severity levels for IAM policy audit findings.
# Ordered from least to most severe: INFO < WARN < CRITICAL.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__IAM__Audit__Severity(str, Enum):
    INFO     = 'INFO'
    WARN     = 'WARN'
    CRITICAL = 'CRITICAL'

    def __str__(self):
        return self.value
