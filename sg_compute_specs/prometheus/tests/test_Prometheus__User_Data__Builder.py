# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Prometheus: tests for Prometheus__User_Data__Builder
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.prometheus.service.Prometheus__User_Data__Builder             import (Prometheus__User_Data__Builder,
                                                                                             PLACEHOLDERS              ,
                                                                                             COMPOSE_DIR               ,
                                                                                             COMPOSE_FILE              ,
                                                                                             PROM_CONFIG_FILE          ,
                                                                                             LOG_FILE                  ,
                                                                                             USER_DATA_TEMPLATE        )


class test_Prometheus__User_Data__Builder(TestCase):

    def setUp(self):
        self.builder = Prometheus__User_Data__Builder()

    def test_placeholders_are_locked(self):
        expected = ('stack_name', 'region', 'log_file',
                    'compose_dir', 'compose_file', 'compose_yaml',
                    'prom_config_file', 'prom_config_yaml',
                    'sidecar_section')
        assert PLACEHOLDERS == expected

    def test_template_contains_all_placeholders(self):
        for p in PLACEHOLDERS:
            assert '{' + p + '}' in USER_DATA_TEMPLATE, f'missing placeholder: {p}'

    def test_render_returns_str(self):
        result = self.builder.render('test-stack', 'eu-west-2', 'compose: {}', 'global: {}')
        assert isinstance(result, str)

    def test_render_substitutes_stack_name(self):
        result = self.builder.render('my-stack', 'eu-west-2', 'y', 'y')
        assert "STACK_NAME='my-stack'" in result

    def test_render_substitutes_region(self):
        result = self.builder.render('s', 'us-east-1', 'y', 'y')
        assert "REGION='us-east-1'" in result

    def test_render_embeds_compose_yaml(self):
        result = self.builder.render('s', 'r', 'services:\n  prometheus: {}', 'global: {}')
        assert 'services:\n  prometheus: {}' in result

    def test_render_embeds_prom_config_yaml(self):
        result = self.builder.render('s', 'r', 'y', 'scrape_interval: 15s')
        assert 'scrape_interval: 15s' in result

    def test_compose_path_constants(self):
        assert COMPOSE_DIR  == '/opt/sg-prometheus'
        assert COMPOSE_FILE == '/opt/sg-prometheus/docker-compose.yml'

    def test_prom_config_file_constant(self):
        assert PROM_CONFIG_FILE == '/opt/sg-prometheus/prometheus.yml'

    def test_log_file_constant(self):
        assert LOG_FILE == '/var/log/sg-prometheus-boot.log'

    def test_render_uses_shebang(self):
        result = self.builder.render('s', 'r', 'y', 'y')
        assert result.startswith('#!/usr/bin/env bash')
