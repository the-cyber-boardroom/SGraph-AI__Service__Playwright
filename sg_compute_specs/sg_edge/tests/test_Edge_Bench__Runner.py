# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge bench: tests for Edge_Bench__Stats + Edge_Bench__Runner
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.sg_edge.bench.Edge_Bench__Runner             import Edge_Bench__Runner
from sg_compute_specs.sg_edge.bench.Edge_Bench__Stats             import Edge_Bench__Stats
from sg_compute_specs.sg_edge.bench.enums.Enum__Edge_Bench__Verdict import Enum__Edge_Bench__Verdict


class test_Edge_Bench__Stats(TestCase):

    def setUp(self):
        self.stats = Edge_Bench__Stats()

    def test_percentile__empty_is_zero(self):
        assert self.stats.percentile([], 95) == 0

    def test_percentile__nearest_rank(self):
        samples = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        assert self.stats.percentile(samples, 50)  == 50
        assert self.stats.percentile(samples, 95)  == 100
        assert self.stats.percentile(samples, 100) == 100

    def test_percentile__unsorted_input(self):
        assert self.stats.percentile([90, 10, 50], 50) == 50


class test_Edge_Bench__Runner(TestCase):

    def setUp(self):
        self.runner = Edge_Bench__Runner()

    def test_evaluate__pass_when_under_target(self):
        m = self.runner.evaluate('F-01', [40000] * 10, target=90000, hard_fail=180000)
        assert m.verdict == Enum__Edge_Bench__Verdict.PASS
        assert int(m.p95) == 40000
        assert m.runs     == 10

    def test_evaluate__warn_between_target_and_hard_fail(self):
        m = self.runner.evaluate('P-06', [3000] * 10, target=2000, hard_fail=5000)
        assert m.verdict == Enum__Edge_Bench__Verdict.WARN

    def test_evaluate__fail_at_or_above_hard_fail(self):
        m = self.runner.evaluate('P-07', [50000] * 10, target=20000, hard_fail=45000)
        assert m.verdict == Enum__Edge_Bench__Verdict.FAIL

    def test_run__aggregates_scenario_samples(self):
        # a deterministic local "scenario": one warm-request measurement
        seq = iter([8, 9, 10, 11, 12])
        def scenario():
            return {'F-02__warm_request': next(seq)}
        report = self.runner.run(scenario, repeat=5,
                                 thresholds={'F-02__warm_request': (50, 200)})
        assert report['passed'] is True
        assert report['metrics'][0].runs == 5
        assert int(report['metrics'][0].p50) in (10, 11)

    def test_run__overall_fails_if_any_metric_fails(self):
        def scenario():
            return {'a': 10, 'b': 999}
        report = self.runner.run(scenario, repeat=3,
                                 thresholds={'a': (50, 100), 'b': (50, 100)})
        assert report['passed'] is False

    def test_run__report_metric_is_json_round_trippable(self):
        from sg_compute_specs.sg_edge.bench.schemas.Schema__Edge_Bench__Metric import Schema__Edge_Bench__Metric
        def scenario():
            return {'m': 5}
        metric   = self.runner.run(scenario, repeat=2, thresholds={'m': (50, 200)})['metrics'][0]
        restored = Schema__Edge_Bench__Metric.from_json(metric.json())
        assert restored.json() == metric.json()
