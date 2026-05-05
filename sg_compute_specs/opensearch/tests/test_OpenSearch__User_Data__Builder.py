# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — OpenSearch: tests for OpenSearch__User_Data__Builder
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.opensearch.service.OpenSearch__User_Data__Builder             import (OpenSearch__User_Data__Builder,
                                                                                             PLACEHOLDERS              ,
                                                                                             COMPOSE_DIR               ,
                                                                                             COMPOSE_FILE              ,
                                                                                             LOG_FILE                  ,
                                                                                             USER_DATA_TEMPLATE        )


class test_OpenSearch__User_Data__Builder(TestCase):

    def setUp(self):
        self.builder = OpenSearch__User_Data__Builder()

    def test_placeholders_are_locked(self):
        expected = ('stack_name', 'region', 'log_file',
                    'compose_dir', 'compose_file', 'compose_yaml',
                    'sidecar_section')
        assert PLACEHOLDERS == expected

    def test_template_contains_all_placeholders(self):
        for p in PLACEHOLDERS:
            assert '{' + p + '}' in USER_DATA_TEMPLATE, f'missing placeholder: {p}'

    def test_render_returns_str(self):
        result = self.builder.render('my-stack', 'eu-west-2', 'services: {}')
        assert isinstance(result, str)

    def test_render_substitutes_stack_name(self):
        result = self.builder.render('my-stack', 'eu-west-2', 'y')
        assert "STACK_NAME='my-stack'" in result

    def test_render_substitutes_region(self):
        result = self.builder.render('s', 'us-east-1', 'y')
        assert "REGION='us-east-1'" in result

    def test_render_embeds_compose_yaml(self):
        result = self.builder.render('s', 'r', 'services:\n  opensearch: {}')
        assert 'services:\n  opensearch: {}' in result

    def test_render_sets_vm_max_map_count(self):
        result = self.builder.render('s', 'r', 'y')
        assert 'vm.max_map_count=262144' in result

    def test_compose_path_constants(self):
        assert COMPOSE_DIR  == '/opt/sg-opensearch'
        assert COMPOSE_FILE == '/opt/sg-opensearch/docker-compose.yml'

    def test_log_file_constant(self):
        assert LOG_FILE == '/var/log/sg-opensearch-boot.log'

    def test_render_uses_shebang(self):
        result = self.builder.render('s', 'r', 'y')
        assert result.startswith('#!/usr/bin/env bash')
