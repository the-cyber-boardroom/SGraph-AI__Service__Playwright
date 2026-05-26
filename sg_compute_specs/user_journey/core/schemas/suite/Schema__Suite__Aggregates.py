# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Schema__Suite__Aggregates (rolled-up metrics for a suite run)
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                                import Type_Safe
from osbot_utils.type_safe.primitives.core.Safe_UInt                                                import Safe_UInt

from sg_compute_specs.playwright.core.schemas.primitives.numeric.Safe_UInt__Milliseconds                 import Safe_UInt__Milliseconds


class Schema__Suite__Aggregates(Type_Safe):                                         # Rolled-up metrics (all default 0)
    latency_p50_ms : Safe_UInt__Milliseconds
    latency_p95_ms : Safe_UInt__Milliseconds
    latency_p99_ms : Safe_UInt__Milliseconds
    flows_total    : Safe_UInt
    flows_blocked  : Safe_UInt
