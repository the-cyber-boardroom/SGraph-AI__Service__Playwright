# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge bench: Enum__Edge_Bench__Verdict
# A scenario metric's verdict against its acceptance thresholds (doc 05):
#   PASS  gate percentile <= target
#   WARN  target < gate percentile < hard_fail   (ship with a known-issues note)
#   FAIL  gate percentile >= hard_fail            (MVP is not shipped)
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Edge_Bench__Verdict(str, Enum):
    PASS = 'pass'
    WARN = 'warn'
    FAIL = 'fail'

    def __str__(self):
        return self.value
