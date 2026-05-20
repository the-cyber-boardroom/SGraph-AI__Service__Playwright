# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge bench: Edge_Bench__Runner
# The doc-05 measurement core: run a scenario N times, collect named integer-ms
# durations, aggregate each into p50/p95/p99, and judge it against its acceptance
# thresholds (target / hard_fail) → a per-metric verdict. This is the part that
# is pure logic and unit-testable; the live AWS / docker-compose scenario bodies
# (P-*/F-*/X-*) and the `sg edge_bench` CLI wiring sit on top of it and need a
# real bench environment to exercise.
#
# A scenario is any callable returning dict[str,int] of {duration_name: ms} for a
# single run. Thresholds is dict[str, (target_ms, hard_fail_ms)]. The gate metric
# is p95 by default (most doc-05 criteria gate on p95/p99).
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Callable

from osbot_utils.type_safe.Type_Safe                                       import Type_Safe

from sg_compute_specs.sg_edge.bench.Edge_Bench__Stats                      import Edge_Bench__Stats
from sg_compute_specs.sg_edge.bench.enums.Enum__Edge_Bench__Verdict        import Enum__Edge_Bench__Verdict
from sg_compute_specs.sg_edge.bench.schemas.Schema__Edge_Bench__Metric     import Schema__Edge_Bench__Metric

DEFAULT_GATE_PERCENTILE = 95                                                         # doc 05 gates most criteria on p95


class Edge_Bench__Runner(Type_Safe):
    stats : Edge_Bench__Stats
    gate  : int = DEFAULT_GATE_PERCENTILE

    def evaluate(self, name: str, samples: list, target: int, hard_fail: int) -> Schema__Edge_Bench__Metric:
        p50  = self.stats.percentile(samples, 50)
        p95  = self.stats.percentile(samples, 95)
        p99  = self.stats.percentile(samples, 99)
        gate = self.stats.percentile(samples, self.gate)
        if   gate >= hard_fail: verdict = Enum__Edge_Bench__Verdict.FAIL
        elif gate >  target   : verdict = Enum__Edge_Bench__Verdict.WARN
        else                  : verdict = Enum__Edge_Bench__Verdict.PASS
        return Schema__Edge_Bench__Metric(name=name, runs=len(samples), p50=p50, p95=p95, p99=p99,
                                          target=target, hard_fail=hard_fail, verdict=verdict)

    def run(self, scenario: Callable, repeat: int, thresholds: dict) -> dict:        # scenario() -> {name: ms}; thresholds[name] = (target, hard_fail)
        collected = {name: [] for name in thresholds}
        for _ in range(repeat):
            sample = scenario() or {}
            for name, ms in sample.items():
                if name in collected:
                    collected[name].append(int(ms))
        metrics = [self.evaluate(name, collected[name], target, hard_fail)
                   for name, (target, hard_fail) in thresholds.items()]
        passed  = all(m.verdict != Enum__Edge_Bench__Verdict.FAIL for m in metrics)
        return {'metrics': metrics, 'passed': passed}
