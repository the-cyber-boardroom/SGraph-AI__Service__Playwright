# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Prometheus__Compose__Template
# Locks the placeholder contract + canonical service / network / volume names
# so future expansion lands as a reviewable diff.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Compose__Template import (CADVISOR_IMAGE         ,
                                                                                                    COMPOSE_TEMPLATE       ,
                                                                                                    NODE_EXPORTER_IMAGE    ,
                                                                                                    PLACEHOLDERS           ,
                                                                                                    PROM_IMAGE             ,
                                                                                                    PROMETHEUS_RETENTION   ,
                                                                                                    Prometheus__Compose__Template)


class test_Prometheus__Compose__Template(TestCase):

    def setUp(self):
        self.tpl = Prometheus__Compose__Template()

    def test_render__substitutes_all_default_images(self):
        out = self.tpl.render()
        assert PROM_IMAGE          in out
        assert CADVISOR_IMAGE      in out
        assert NODE_EXPORTER_IMAGE in out

    def test_render__24h_default_retention(self):                                   # P2: 24h Prometheus self-prune
        assert PROMETHEUS_RETENTION == '24h'
        out = self.tpl.render()
        assert '--storage.tsdb.retention.time=24h' in out

    def test_render__custom_retention(self):
        out = self.tpl.render(retention='7d')
        assert '--storage.tsdb.retention.time=7d' in out

    def test_render__custom_images(self):                                           # Tests can pin known versions
        out = self.tpl.render(prom_image='prom/prometheus:v2.51.0',
                              cadvisor_image='gcr.io/cadvisor/cadvisor:v0.49.0',
                              node_exporter_image='prom/node-exporter:v1.8.0')
        assert 'prom/prometheus:v2.51.0' in out
        assert 'cadvisor:v0.49.0'        in out
        assert 'node-exporter:v1.8.0'    in out

    def test_render__no_placeholders_leaked(self):
        out      = self.tpl.render()
        leftover = re.findall(r'\{([a-z_]+)\}', out)
        assert leftover == []

    def test_render__includes_canonical_container_names(self):                      # sp prom exec / connect target these
        out = self.tpl.render()
        assert 'container_name: sg-prometheus'    in out
        assert 'container_name: sg-cadvisor'      in out
        assert 'container_name: sg-node-exporter' in out

    def test_render__shared_network_named_sg_net(self):                             # Same convention as the playwright + sp os stacks
        out = self.tpl.render()
        assert '- sg-net' in out
        assert 'sg-net:'  in out

    def test_render__no_dashboards_or_grafana_container(self):                      # P1: no UI in this stack
        out = self.tpl.render()
        assert 'grafana'    not in out.lower()
        assert 'dashboards' not in out.lower()

    def test_render__bind_mounts_prometheus_yml(self):                              # prometheus.yml is rendered upstream + dropped on disk by user-data
        out = self.tpl.render()
        assert '/opt/sg-prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro' in out

    def test_render__exposes_port_9090(self):                                       # Public Prom UI / API
        out = self.tpl.render()
        assert '"9090:9090"' in out

    def test_template_placeholders_match_PLACEHOLDERS_constant(self):
        in_template = set(re.findall(r'\{([a-z_]+)\}', COMPOSE_TEMPLATE))
        assert in_template == set(PLACEHOLDERS)
