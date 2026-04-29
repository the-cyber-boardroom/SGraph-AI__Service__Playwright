# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Prometheus__Config__Generator
# Pure mapper — no AWS / HTTP calls. Locks the baseline scrape jobs (cadvisor +
# node-exporter) and the format of caller-supplied scrape_targets.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.prometheus.collections.List__Schema__Prom__Scrape__Target import List__Schema__Prom__Scrape__Target
from sgraph_ai_service_playwright__cli.prometheus.collections.List__Str             import List__Str
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Scrape__Target import Schema__Prom__Scrape__Target
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Config__Generator import (SCRAPE_INTERVAL,
                                                                                                  Prometheus__Config__Generator)


class test_Prometheus__Config__Generator(TestCase):

    def setUp(self):
        self.gen = Prometheus__Config__Generator()

    def test_render__defaults_to_baseline_only(self):                               # No targets passed → just the two local exporters
        out = self.gen.render()
        assert f'scrape_interval: {SCRAPE_INTERVAL}'   in out
        assert "- job_name: cadvisor"                  in out
        assert "- targets: ['cadvisor:8080']"          in out
        assert "- job_name: node-exporter"             in out
        assert "- targets: ['node-exporter:9100']"     in out

    def test_render__empty_target_list_yields_baseline_only(self):
        out = self.gen.render(List__Schema__Prom__Scrape__Target())
        assert "- job_name: cadvisor"        in out
        assert "playwright"             not in out                                  # No baked targets means no extra jobs

    def test_render__appends_one_baked_target(self):
        hosts = List__Str(); hosts.append('1.2.3.4:8000')
        targets = List__Schema__Prom__Scrape__Target()
        targets.append(Schema__Prom__Scrape__Target(job_name='playwright', targets=hosts))

        out = self.gen.render(targets)
        assert "- job_name: playwright"        in out
        assert "scheme: http"                  in out
        assert "metrics_path: /metrics"        in out
        assert "- targets: ['1.2.3.4:8000']"   in out

    def test_render__appends_multiple_targets_in_order(self):
        h1 = List__Str(); h1.append('1.1.1.1:8000')
        h2 = List__Str(); h2.append('2.2.2.2:9100'); h2.append('2.2.2.3:9100')
        targets = List__Schema__Prom__Scrape__Target()
        targets.append(Schema__Prom__Scrape__Target(job_name='alpha', targets=h1))
        targets.append(Schema__Prom__Scrape__Target(job_name='beta',  targets=h2, scheme='https', metrics_path='/api/metrics'))

        out = self.gen.render(targets)
        assert "- job_name: alpha"                                in out
        assert "- targets: ['1.1.1.1:8000']"                       in out
        assert "- job_name: beta"                                  in out
        assert "scheme: https"                                     in out
        assert "metrics_path: /api/metrics"                        in out
        assert "- targets: ['2.2.2.2:9100', '2.2.2.3:9100']"        in out
        assert out.index('alpha') < out.index('beta')                                # Order preserved

    def test_render__baseline_jobs_always_appear_before_baked_targets(self):
        h = List__Str(); h.append('1.2.3.4:8000')
        targets = List__Schema__Prom__Scrape__Target()
        targets.append(Schema__Prom__Scrape__Target(job_name='zzz-late', targets=h))
        out = self.gen.render(targets)
        assert out.index('cadvisor')      < out.index('zzz-late')
        assert out.index('node-exporter') < out.index('zzz-late')

    def test_render__quotes_host_port_targets_singly(self):                         # Prometheus YAML accepts single-quoted strings; double-quoted host:port can confuse the YAML parser when the port needs quoting
        h = List__Str(); h.append('host.example:9100')
        targets = List__Schema__Prom__Scrape__Target()
        targets.append(Schema__Prom__Scrape__Target(job_name='ext', targets=h))
        out = self.gen.render(targets)
        assert "- targets: ['host.example:9100']" in out
