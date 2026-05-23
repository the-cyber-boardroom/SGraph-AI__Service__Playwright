# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Enum__Sentinel__Verdict
# L1's decision for a request. MVP only: allow | block ('flag' deferred).
# ═══════════════════════════════════════════════════════════════════════════════

from enum import Enum


class Enum__Sentinel__Verdict(str, Enum):
    ALLOW = 'allow'
    BLOCK = 'block'
