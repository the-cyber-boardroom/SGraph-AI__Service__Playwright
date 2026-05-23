# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__Traffic__Report__Builder
# PURE aggregation of traffic results → Schema__Traffic__Report (accuracy + latency).
# No I/O, no node — unit-testable on any Python. Percentiles use nearest-rank.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.sentinel.enums.Enum__Sentinel__Verdict          import Enum__Sentinel__Verdict
from sgraph_ai_service_playwright__cli.sentinel.traffic.enums.Enum__Traffic__Category  import Enum__Traffic__Category
from sgraph_ai_service_playwright__cli.sentinel.traffic.schemas.Schema__Traffic__Report import Schema__Traffic__Report

BLOCK  = Enum__Sentinel__Verdict.BLOCK
BENIGN = Enum__Traffic__Category.BENIGN


def _percentile(sorted_vals: list, pct: float) -> float:
    if not sorted_vals:
        return 0.0
    k = max(0, min(len(sorted_vals) - 1, int(round((pct / 100.0) * len(sorted_vals) + 0.5)) - 1))
    return sorted_vals[k]


class Sentinel__Traffic__Report__Builder(Type_Safe):

    def build(self, results, mode: str) -> Schema__Traffic__Report:
        report = Schema__Traffic__Report(mode=mode, total=len(results))
        latencies = []
        for r in results:
            latencies.append(float(r.latency_ms))
            if r.observed_verdict == BLOCK:
                report.blocked += 1
            else:
                report.allowed += 1
            if r.matched:
                report.matched += 1
            is_benign = (r.category == BENIGN)
            if is_benign:
                report.benign_total += 1
                if r.observed_verdict != BLOCK:
                    report.benign_allowed += 1
            else:                                                                    # malicious or malformed → should block
                report.malicious_total += 1
                if r.observed_verdict == BLOCK:
                    report.malicious_blocked += 1

        if report.total:
            report.accuracy_pct = round(100.0 * report.matched / report.total, 1)
        if latencies:
            ordered                = sorted(latencies)
            report.latency_min_ms  = round(ordered[0], 3)
            report.latency_max_ms  = round(ordered[-1], 3)
            report.latency_avg_ms  = round(sum(ordered) / len(ordered), 3)
            report.latency_p50_ms  = round(_percentile(ordered, 50), 3)
            report.latency_p95_ms  = round(_percentile(ordered, 95), 3)
        return report
