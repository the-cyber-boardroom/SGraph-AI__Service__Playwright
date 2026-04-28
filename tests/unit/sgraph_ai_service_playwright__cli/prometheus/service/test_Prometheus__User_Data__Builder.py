# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Prometheus__User_Data__Builder
# Locks the placeholder contract + the install-step structure. Both compose
# YAML and prometheus.yml are taken as input (rendered upstream by Compose
# template + Config generator).
# ═══════════════════════════════════════════════════════════════════════════════

import re

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__User_Data__Builder import (COMPOSE_DIR             ,
                                                                                                    COMPOSE_FILE             ,
                                                                                                    LOG_FILE                 ,
                                                                                                    PLACEHOLDERS             ,
                                                                                                    PROM_CONFIG_FILE         ,
                                                                                                    USER_DATA_TEMPLATE       ,
                                                                                                    Prometheus__User_Data__Builder)


SAMPLE_COMPOSE_YAML = "services:\n  prometheus:\n    image: prom/prometheus:latest\n"
SAMPLE_PROM_CONFIG  = "global:\n  scrape_interval: 15s\nscrape_configs: []\n"


class test_Prometheus__User_Data__Builder(TestCase):

    def setUp(self):
        self.builder = Prometheus__User_Data__Builder()

    def _out(self):
        return self.builder.render('prom-quiet-fermi', 'eu-west-2', SAMPLE_COMPOSE_YAML, SAMPLE_PROM_CONFIG)

    # ── shape ─────────────────────────────────────────────────────────────────

    def test_render__starts_with_shebang(self):
        assert self._out().startswith('#!/usr/bin/env bash\n')

    def test_render__sets_strict_bash(self):
        assert 'set -euo pipefail' in self._out()

    def test_render__logs_to_canonical_path(self):
        assert LOG_FILE                          in self._out()
        assert '/var/log/sg-prometheus-boot.log' == LOG_FILE

    # ── substitutions ─────────────────────────────────────────────────────────

    def test_render__substitutes_stack_and_region(self):
        out = self._out()
        assert "STACK_NAME='prom-quiet-fermi'" in out
        assert "REGION='eu-west-2'"            in out

    def test_render__embeds_compose_yaml_in_heredoc(self):
        out = self._out()
        assert 'cat > /opt/sg-prometheus/docker-compose.yml' in out
        assert "<<'SG_PROM_COMPOSE_EOF'"                     in out
        assert SAMPLE_COMPOSE_YAML.strip()                   in out
        assert 'SG_PROM_COMPOSE_EOF\n'                       in out

    def test_render__embeds_prometheus_yml_in_heredoc(self):
        out = self._out()
        assert 'cat > /opt/sg-prometheus/prometheus.yml' in out
        assert "<<'SG_PROM_CONFIG_EOF'"                  in out
        assert SAMPLE_PROM_CONFIG.strip()                in out
        assert 'SG_PROM_CONFIG_EOF\n'                    in out

    def test_render__no_placeholders_leaked(self):
        leftover = re.findall(r'\{([a-z_]+)\}', self._out())
        assert leftover == []

    # ── install steps ─────────────────────────────────────────────────────────

    def test_render__installs_docker_via_dnf(self):
        out = self._out()
        assert 'dnf install -y docker'         in out
        assert 'systemctl enable --now docker' in out

    def test_render__installs_compose_plugin(self):
        out = self._out()
        assert '/usr/local/lib/docker/cli-plugins/docker-compose' in out
        assert 'chmod +x'                                          in out

    def test_render__does_not_bump_vm_max_map_count(self):                          # Prom doesn't need it (that's an OS 2.x requirement)
        out = self._out()
        assert 'vm.max_map_count' not in out

    def test_render__compose_up_runs_in_compose_dir(self):
        out = self._out()
        assert COMPOSE_DIR             in out
        assert 'docker compose up -d'  in out

    # ── contract ──────────────────────────────────────────────────────────────

    def test_template_placeholders_match_PLACEHOLDERS_constant(self):
        in_template = set(re.findall(r'\{([a-z_]+)\}', USER_DATA_TEMPLATE))
        assert in_template == set(PLACEHOLDERS)

    def test_canonical_paths_are_under_opt_sg_prometheus(self):                     # /opt/sg-{service} convention shared with other stacks
        assert COMPOSE_DIR        == '/opt/sg-prometheus'
        assert COMPOSE_FILE       == '/opt/sg-prometheus/docker-compose.yml'
        assert PROM_CONFIG_FILE   == '/opt/sg-prometheus/prometheus.yml'
