# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Docker__User_Data__Builder
# Pure template renderer — no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.docker.service.Docker__User_Data__Builder    import (Docker__User_Data__Builder ,
                                                                                               HOST_CONTROL_IMAGE        ,
                                                                                               PLACEHOLDERS              ,
                                                                                               USER_DATA_TEMPLATE        )


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

    def test_render__embeds_host_control_image(self):
        result = self.builder.render('fast-fermi', 'eu-west-2', registry='123.dkr.ecr.eu-west-2.amazonaws.com')
        assert HOST_CONTROL_IMAGE in result
        assert '9000:8000' in result

    def test_render__embeds_registry(self):
        result = self.builder.render('fast-fermi', 'eu-west-2', registry='123.dkr.ecr.eu-west-2.amazonaws.com')
        assert '123.dkr.ecr.eu-west-2.amazonaws.com' in result

    def test_render__embeds_api_key(self):
        result = self.builder.render('fast-fermi', 'eu-west-2', api_key_name='X-API-Key', api_key_value='abc123')
        assert 'abc123'    in result
        assert 'X-API-Key' in result

    def test_placeholders_locked(self):
        assert PLACEHOLDERS == ('stack_name', 'region', 'registry', 'host_control_image',
                                'api_key_name', 'api_key_value',
                                'log_file', 'shutdown_line')

    def test_template_has_all_placeholders(self):
        for p in PLACEHOLDERS:
            assert f'{{{p}}}' in USER_DATA_TEMPLATE

    def test_render__shutdown_timer_included_when_max_hours_set(self):
        result = self.builder.render('fast-fermi', 'eu-west-2', max_hours=1)
        assert 'shutdown -h +60' in result

    def test_render__no_shutdown_when_max_hours_zero(self):
        result = self.builder.render('fast-fermi', 'eu-west-2', max_hours=0)
        assert 'shutdown -h' not in result
        assert 'no auto-terminate' in result

    def test_schema__default_max_hours_is_one(self):
        from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__Create__Request import Schema__Docker__Create__Request
        assert Schema__Docker__Create__Request().max_hours == 1
