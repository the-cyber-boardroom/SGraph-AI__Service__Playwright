# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: Enum__Local__Edge__Severity
# Severity for a check issue (drives the icon/colour in the `sg edge local check`
# ASCII report). OK = no problem; INFO = expected non-error state worth surfacing.
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Local__Edge__Severity(str, Enum):
    OK    = 'ok'
    INFO  = 'info'
    WARN  = 'warn'
    ERROR = 'error'

    def __str__(self):
        return self.value
