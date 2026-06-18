# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Content_Proxy__Traffic__Report__Builder
# Pure aggregation: list of results → accuracy + latency report. No I/O.
# ═══════════════════════════════════════════════════════════════════════════════

import math

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sg_compute_specs.content_proxy.traffic.Schema__Content_Proxy__Traffic__Report   import Schema__Content_Proxy__Traffic__Report


def _percentile(sorted_values, pct: float) -> int:                                 # nearest-rank (ceil)
    if not sorted_values:
        return 0
    rank = max(1, math.ceil(pct / 100.0 * len(sorted_values)))
    rank = min(rank, len(sorted_values))
    return int(sorted_values[rank - 1])


class Content_Proxy__Traffic__Report__Builder(Type_Safe):

    def build(self, results) -> Schema__Content_Proxy__Traffic__Report:            # results = iterable of Schema__...__Traffic__Result
        results   = list(results)
        total     = len(results)
        passed    = sum(1 for r in results if r.passed)
        latencies = sorted(int(r.latency_ms) for r in results)
        report = Schema__Content_Proxy__Traffic__Report()
        report.total          = total
        report.passed         = passed
        report.failed         = total - passed
        report.accuracy_pct   = round(100.0 * passed / total, 1) if total else 0.0
        report.latency_p50_ms = _percentile(latencies, 50)
        report.latency_p95_ms = _percentile(latencies, 95)
        return report
