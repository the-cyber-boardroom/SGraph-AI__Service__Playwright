# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge bench: Edge_Bench__Stats
# Percentile helper for the bench. Nearest-rank method over a list of integer-ms
# samples (doc 05 reports p50/p95/p99). Small and dependency-free so the harness
# stays single-purpose.
# ═══════════════════════════════════════════════════════════════════════════════

import math

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Edge_Bench__Stats(Type_Safe):

    def percentile(self, samples: list, p: int) -> int:                              # nearest-rank percentile; 0 for empty input
        if not samples:
            return 0
        ordered = sorted(int(s) for s in samples)
        rank    = max(1, math.ceil((p / 100.0) * len(ordered)))                      # 1-based rank, clamped to >=1
        rank    = min(rank, len(ordered))
        return ordered[rank - 1]
