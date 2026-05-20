# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge bench: Schema__Edge_Bench__Metric
# One measured metric across a scenario's repeated runs: the p50/p95/p99 of the
# collected samples (whole ms), the target / hard-fail thresholds it was judged
# against, and the resulting verdict. This is the structured-JSON unit doc 05
# wants — diffable across runs, machine-checkable in CI. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                          import Type_Safe

from sg_compute_specs.sg_edge.bench.enums.Enum__Edge_Bench__Verdict           import Enum__Edge_Bench__Verdict
from sg_compute_specs.sg_edge.bench.primitives.Safe_Int__Edge_Bench__Millis   import Safe_Int__Edge_Bench__Millis


class Schema__Edge_Bench__Metric(Type_Safe):
    name      : str                          = ''                               # e.g. 'F-01__total_end_to_end'
    runs      : int                          = 0                                # number of samples
    p50       : Safe_Int__Edge_Bench__Millis = Safe_Int__Edge_Bench__Millis()
    p95       : Safe_Int__Edge_Bench__Millis = Safe_Int__Edge_Bench__Millis()
    p99       : Safe_Int__Edge_Bench__Millis = Safe_Int__Edge_Bench__Millis()
    target    : Safe_Int__Edge_Bench__Millis = Safe_Int__Edge_Bench__Millis()   # 'target' threshold (doc 05)
    hard_fail : Safe_Int__Edge_Bench__Millis = Safe_Int__Edge_Bench__Millis()   # 'hard fail' threshold (doc 05)
    verdict   : Enum__Edge_Bench__Verdict    = Enum__Edge_Bench__Verdict.PASS
