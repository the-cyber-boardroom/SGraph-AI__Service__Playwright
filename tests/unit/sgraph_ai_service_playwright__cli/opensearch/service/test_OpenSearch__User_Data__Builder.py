# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for OpenSearch__User_Data__Builder
# Locks the placeholder contract + the install-step structure. The compose
# YAML is taken as input (rendered upstream by OpenSearch__Compose__Template).
# admin_password lives only inside compose_yaml — secrets in one place.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__User_Data__Builder import (COMPOSE_DIR             ,
                                                                                                    COMPOSE_FILE             ,
                                                                                                    LOG_FILE                 ,
                                                                                                    PLACEHOLDERS             ,
                                                                                                    USER_DATA_TEMPLATE       ,
                                                                                                    OpenSearch__User_Data__Builder)


SAMPLE_COMPOSE_YAML = "services:\n  opensearch:\n    image: opensearchproject/opensearch:latest\n"


class test_OpenSearch__User_Data__Builder(TestCase):

    def setUp(self):
        self.builder = OpenSearch__User_Data__Builder()

    def _out(self):
        return self.builder.render('os-quiet-fermi', 'eu-west-2', SAMPLE_COMPOSE_YAML)

    # ── shape ─────────────────────────────────────────────────────────────────

    def test_render__starts_with_shebang(self):
        assert self._out().startswith('#!/usr/bin/env bash\n')

    def test_render__sets_strict_bash(self):
        assert 'set -euo pipefail' in self._out()

    def test_render__logs_to_canonical_path(self):
        assert LOG_FILE                          in self._out()
        assert '/var/log/sg-opensearch-boot.log' == LOG_FILE                        # Lock the canonical path

    # ── substitutions ─────────────────────────────────────────────────────────

    def test_render__substitutes_stack_and_region(self):
        out = self._out()
        assert "STACK_NAME='os-quiet-fermi'" in out
        assert "REGION='eu-west-2'"          in out

    def test_render__embeds_compose_yaml_in_heredoc(self):
        out = self._out()
        assert 'cat > /opt/sg-opensearch/docker-compose.yml' in out
        assert "<<'SG_OS_COMPOSE_EOF'"                       in out
        assert SAMPLE_COMPOSE_YAML.strip()                   in out
        assert 'SG_OS_COMPOSE_EOF\n'                          in out

    def test_render__no_placeholders_leaked(self):                                  # Defensive: every {key} substituted
        leftover = re.findall(r'\{([a-z_]+)\}', self._out())
        assert leftover == []

    # ── install steps ─────────────────────────────────────────────────────────

    def test_render__installs_docker_via_dnf(self):                                 # AL2023 uses dnf, not yum/apt
        out = self._out()
        assert 'dnf install -y docker'        in out
        assert 'systemctl enable --now docker' in out

    def test_render__installs_compose_plugin(self):                                 # Compose CLI plugin lives under /usr/local/lib/docker/cli-plugins/
        out = self._out()
        assert '/usr/local/lib/docker/cli-plugins/docker-compose' in out
        assert 'chmod +x'                                          in out

    def test_render__bumps_vm_max_map_count(self):                                  # OpenSearch 2.x requires >= 262144 or refuses to start
        out = self._out()
        assert 'sysctl -w vm.max_map_count=262144'                in out
        assert 'vm.max_map_count=262144" >> /etc/sysctl.d/99-sg-opensearch.conf' in out

    def test_render__compose_up_runs_in_compose_dir(self):
        out = self._out()
        assert COMPOSE_DIR             in out
        assert 'docker compose up -d'  in out

    def test_render__does_not_carry_admin_password(self):                           # admin_password belongs in compose_yaml only — secrets in one place
        out = self._out()
        assert 'ADMIN_PASSWORD'  not in out
        assert 'admin_password'  not in out                                         # Defensive — also no Python-style leftover

    # ── contract ──────────────────────────────────────────────────────────────

    def test_template_placeholders_match_PLACEHOLDERS_constant(self):
        in_template = set(re.findall(r'\{([a-z_]+)\}', USER_DATA_TEMPLATE))
        assert in_template == set(PLACEHOLDERS)

    def test_canonical_paths_are_under_opt_sg_opensearch(self):                     # /opt/sg-{service} convention shared with playwright EC2 stack
        assert COMPOSE_DIR  == '/opt/sg-opensearch'
        assert COMPOSE_FILE == '/opt/sg-opensearch/docker-compose.yml'
