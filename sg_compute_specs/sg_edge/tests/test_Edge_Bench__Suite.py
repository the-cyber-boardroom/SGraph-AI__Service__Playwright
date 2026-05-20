# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge bench: tests for Edge_Bench__Suite + the local scenarios
# Runs the Slice-6 local scenarios against real temp-dir `sg edge local` stacks
# (no AWS, no docker, no mocks). Asserts: every local scenario passes, each emits
# the expected metric names, aws-bench scenarios skip cleanly, a broken edge fails
# fast, and the registry/catalog is well-formed. Pure Python — runs on 3.11 too.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.sg_edge.bench.Edge_Bench__Suite                import Edge_Bench__Suite
from sg_compute_specs.sg_edge.bench.enums.Enum__Edge_Bench__Target   import Enum__Edge_Bench__Target
from sg_compute_specs.sg_edge.bench.enums.Enum__Edge_Bench__Tier     import Enum__Edge_Bench__Tier
from sg_compute_specs.sg_edge.bench.scenarios.Edge_Bench__Scenarios  import SCENARIOS, descriptors

LOCAL     = Enum__Edge_Bench__Target.LOCAL
AWS_BENCH = Enum__Edge_Bench__Target.AWS_BENCH

LOCAL_IDS = ['P-03', 'P-07', 'P-12', 'F-01', 'F-06', 'F-08', 'X-07', 'X-12']
EXPECTED_METRICS = {
    'P-03': {'dns_write', 'dns_read'},
    'P-07': {'response'},
    'P-12': {'response'},
    'F-01': {'setup', 'register', 'request', 'total'},
    'F-06': {'cycle_total'},
    'F-08': {'response'},
    'X-07': {'response'},
    'X-12': {'enumeration_50'},
}


class test_Edge_Bench__Scenarios__registry(TestCase):

    def test_every_local_scenario_has_a_make_and_thresholds(self):
        for sid in LOCAL_IDS:
            entry = SCENARIOS[sid]
            assert entry['descriptor'].target == LOCAL
            assert entry['make'] is not None
            assert entry['thresholds'], f'{sid} has no thresholds'

    def test_aws_bench_scenarios_have_no_make(self):
        for entry in SCENARIOS.values():
            if entry['descriptor'].target == AWS_BENCH:
                assert entry['make'] is None

    def test_descriptors_filter_by_target_and_tier(self):
        assert {d.id for d in descriptors(target=LOCAL)} == set(LOCAL_IDS)
        prim_local = {d.id for d in descriptors(target=LOCAL, tier=Enum__Edge_Bench__Tier.PRIMITIVE)}
        assert prim_local == {'P-03', 'P-07', 'P-12'}


class test_Edge_Bench__Suite__local(TestCase):

    def setUp(self):
        self.suite = Edge_Bench__Suite()

    def test_each_local_scenario_passes_and_emits_metrics(self):
        for sid in LOCAL_IDS:
            result = self.suite.run_scenario(sid, repeat=2, target=LOCAL)
            assert result.skipped is False,                 f'{sid} unexpectedly skipped: {result.note}'
            assert result.passed  is True,                  f'{sid} failed: {result.note}'
            assert result.runs    == 2
            names = {m.name for m in result.metrics}
            assert names == EXPECTED_METRICS[sid],          f'{sid} metrics {names} != {EXPECTED_METRICS[sid]}'

    def test_aws_bench_scenario_skips_on_local_target(self):
        result = self.suite.run_scenario('P-01', repeat=2, target=LOCAL)
        assert result.skipped is True
        assert 'aws-bench' in result.note

    def test_aws_bench_target_skips_with_no_backend(self):
        result = self.suite.run_scenario('P-03', repeat=2, target=AWS_BENCH)         # local scenario, aws-bench target → skip
        assert result.skipped is True

    def test_unknown_scenario_raises(self):
        with self.assertRaises(ValueError):
            self.suite.run_scenario('ZZ-99')

    def test_run_tier_primitives(self):
        suite = self.suite.run_tier(Enum__Edge_Bench__Tier.PRIMITIVE, repeat=2, target=LOCAL)
        ran = [r for r in suite.results if not r.skipped]
        assert suite.passed is True
        assert {r.id for r in ran} == {'P-03', 'P-07', 'P-12'}

    def test_run_all_local(self):
        suite = self.suite.run_all(repeat=1, target=LOCAL)
        ran     = [r for r in suite.results if not r.skipped]
        skipped = [r for r in suite.results if r.skipped]
        assert suite.passed is True
        assert {r.id for r in ran} == set(LOCAL_IDS)
        assert len(skipped) == 8                                                     # the aws-bench-only scenarios
        assert suite.run_id                                                          # a run id was generated

    def test_verdicts_are_pass_under_generous_local_budgets(self):
        result = self.suite.run_scenario('F-01', repeat=3, target=LOCAL)
        for m in result.metrics:
            assert str(m.verdict) == 'pass', f'{m.name} verdict={m.verdict} p95={int(m.p95)}'
