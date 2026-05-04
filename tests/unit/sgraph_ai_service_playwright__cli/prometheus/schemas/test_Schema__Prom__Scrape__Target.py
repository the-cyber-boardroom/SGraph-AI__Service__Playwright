# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Schema__Prom__Scrape__Target
# Defaults + round-trip via .json() so the prometheus.yml renderer in 6f gets
# a stable shape to work from.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.prometheus.collections.List__Str             import List__Str
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Scrape__Target import Schema__Prom__Scrape__Target


class test_Schema__Prom__Scrape__Target(TestCase):

    def test__defaults(self):
        t = Schema__Prom__Scrape__Target()
        assert str(t.job_name)     == ''
        assert list(t.targets)     == []
        assert str(t.scheme)       == 'http'
        assert str(t.metrics_path) == '/metrics'

    def test__round_trip_via_json(self):
        targets = List__Str()
        targets.append('1.2.3.4:8000')
        targets.append('1.2.3.4:8001')
        original = Schema__Prom__Scrape__Target(job_name     = 'playwright',
                                                 targets      = targets,
                                                 scheme       = 'https',
                                                 metrics_path = '/api/metrics')
        again = Schema__Prom__Scrape__Target.from_json(original.json())
        assert str(again.job_name)     == 'playwright'
        assert list(again.targets)     == ['1.2.3.4:8000', '1.2.3.4:8001']
        assert str(again.scheme)       == 'https'
        assert str(again.metrics_path) == '/api/metrics'                            # Leading slash preserved
