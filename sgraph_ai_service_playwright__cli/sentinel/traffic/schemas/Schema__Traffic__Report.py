# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Schema__Traffic__Report
# Aggregate measurement of a traffic run: decision accuracy (did malicious get
# blocked / benign pass) and latency stats. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe               import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_Str import Safe_Str


class Schema__Traffic__Report(Type_Safe):
    mode              : Safe_Str                                                     # 'local' (in-process) | 'http'
    total             : int   = 0
    allowed           : int   = 0
    blocked           : int   = 0
    matched           : int   = 0                                                    # decisions equal to expectation
    accuracy_pct      : float = 0.0
    malicious_total   : int   = 0
    malicious_blocked : int   = 0
    benign_total      : int   = 0
    benign_allowed    : int   = 0
    latency_min_ms    : float = 0.0
    latency_avg_ms    : float = 0.0
    latency_p50_ms    : float = 0.0
    latency_p95_ms    : float = 0.0
    latency_max_ms    : float = 0.0
