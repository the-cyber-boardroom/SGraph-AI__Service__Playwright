# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Docker__User_Data__Builder
# Pure template renderer — no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.docker.service.Docker__User_Data__Builder    import (Docker__User_Data__Builder,
                                                                                               PLACEHOLDERS            ,
                                                                                               USER_DATA_TEMPLATE       )


class test_Docker__User_Data__Builder(TestCase):

    def setUp(self):
        self.builder = Docker__User_Data__Builder()

    def test_render__starts_with_shebang(self):
        result = self.builder.render('fast-fermi', 'eu-west-2')
        assert result.startswith('#!/usr/bin/env bash')

    def test_render__installs_docker(self):
        result = self.builder.render('fast-fermi', 'eu-west-2')
        assert 'dnf install -y docker' in result

    def test_render__installs_compose_plugin(self):
        result = self.builder.render('fast-fermi', 'eu-west-2')
        assert 'docker-compose' in result

    def test_render__enables_ssm_agent(self):
        result = self.builder.render('fast-fermi', 'eu-west-2')
        assert 'amazon-ssm-agent' in result

    def test_render__embeds_stack_name_and_region(self):
        result = self.builder.render('fast-fermi', 'eu-west-2')
        assert 'fast-fermi' in result
        assert 'eu-west-2'  in result

    def test_placeholders_locked(self):
        assert PLACEHOLDERS == ('stack_name', 'region', 'log_file')

    def test_template_has_all_placeholders(self):
        for p in PLACEHOLDERS:
            assert f'{{{p}}}' in USER_DATA_TEMPLATE
