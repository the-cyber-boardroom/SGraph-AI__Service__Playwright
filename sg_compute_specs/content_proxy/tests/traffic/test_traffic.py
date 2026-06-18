# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: traffic corpus + report tests (pure)
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib                                                                        import Path
from unittest                                                                       import TestCase

import sg_compute_specs.content_proxy.traffic                                        as traffic_pkg
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Flow__Action          import Enum__Content_Proxy__Flow__Action
from sg_compute_specs.content_proxy.traffic.Content_Proxy__Traffic__Corpus           import default_cases
from sg_compute_specs.content_proxy.traffic.Content_Proxy__Traffic__Report__Builder  import Content_Proxy__Traffic__Report__Builder
from sg_compute_specs.content_proxy.traffic.Content_Proxy__Traffic__Runner           import Content_Proxy__Traffic__Runner


A = Enum__Content_Proxy__Flow__Action


class test_corpus(TestCase):

    def test_default_cases_and_fixtures_exist(self):
        cases = default_cases()
        assert len(cases) >= 4
        labels = {str(c.label) for c in cases}
        assert {'should-blur', 'should-pass', 'should-skip'} <= labels
        pkg_dir = Path(traffic_pkg.__file__).parent
        for c in cases:
            assert (pkg_dir / str(c.url)).exists(), c.url                           # every fixture is present


class test_runner_and_report(TestCase):

    def test_all_correct_is_100pct(self):
        cases    = default_cases()
        observed = {str(c.name): (c.expected, 40) for c in cases}                   # everything graded correct
        results  = Content_Proxy__Traffic__Runner().build_results(cases, observed)
        report   = Content_Proxy__Traffic__Report__Builder().build(results)
        assert report.total        == len(cases)
        assert report.passed       == len(cases)
        assert report.failed       == 0
        assert report.accuracy_pct == 100.0

    def test_one_wrong_lowers_accuracy(self):
        cases    = default_cases()
        observed = {str(c.name): (c.expected, 10) for c in cases}
        # break the should-pass case: proxy wrongly injected
        observed['plain_article'] = (A.INJECTED, 10)
        results = Content_Proxy__Traffic__Runner().build_results(cases, observed)
        report  = Content_Proxy__Traffic__Report__Builder().build(results)
        assert report.failed == 1
        assert report.accuracy_pct < 100.0
        failed = [r for r in results if not r.passed][0]
        assert str(failed.case_name) == 'plain_article'
        assert failed.observed == A.INJECTED and failed.expected == A.PASSED

    def test_latency_percentiles(self):
        cases    = default_cases()[:1]
        # synthesize many results with known latencies via build_results on a single case repeated
        runner   = Content_Proxy__Traffic__Runner()
        results  = []
        for ms in (10, 20, 30, 40, 100):
            r = runner.build_results(cases, {str(cases[0].name): (cases[0].expected, ms)})[0]
            results.append(r)
        report = Content_Proxy__Traffic__Report__Builder().build(results)
        assert report.latency_p50_ms == 30
        assert report.latency_p95_ms == 100
