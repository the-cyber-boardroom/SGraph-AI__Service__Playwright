# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Docker: tests for Docker__User_Data__Builder
# Pure template renderer — no AWS calls.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.docker.service.Docker__User_Data__Builder                     import (Docker__User_Data__Builder,
                                                                                              PLACEHOLDERS            ,
                                                                                              BASE_TEMPLATE           ,
                                                                                              FOOTER_TEMPLATE         )


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
        assert PLACEHOLDERS == ('stack_name', 'region', 'log_file', 'shutdown_line')

    def test_render__no_sidecar_when_registry_empty(self):
        result = self.builder.render('fast-fermi', 'eu-west-2')
        assert 'sg-sidecar' not in result
        assert 'ecr'        not in result

    def test_render__sidecar_included_when_registry_set(self):
        result = self.builder.render('fast-fermi', 'eu-west-2',
                                     registry      = '1234.dkr.ecr.eu-west-2.amazonaws.com',
                                     api_key_value = 'secret-key')
        assert 'sg-sidecar'   in result
        assert '1234.dkr.ecr' in result
        assert 'secret-key'   in result
        assert 'X-API-Key'    in result
        assert '19009:8000'   in result
        assert 'rm -f /root/.docker/config.json' in result

    def test_render__shutdown_timer_included_when_max_hours_set(self):
        result = self.builder.render('fast-fermi', 'eu-west-2', max_hours=1)
        assert 'shutdown -h +60' in result

    def test_render__no_shutdown_when_max_hours_zero(self):
        result = self.builder.render('fast-fermi', 'eu-west-2', max_hours=0)
        assert 'shutdown -h' not in result
        assert 'no auto-terminate' in result

    def test_schema__default_max_hours_is_one(self):
        from sg_compute_specs.docker.schemas.Schema__Docker__Create__Request import Schema__Docker__Create__Request
        assert Schema__Docker__Create__Request().max_hours == 1

    def test_schema__registry_and_api_key_fields_exist(self):
        from sg_compute_specs.docker.schemas.Schema__Docker__Create__Request import Schema__Docker__Create__Request
        req = Schema__Docker__Create__Request()
        assert req.registry      == ''
        assert req.api_key_name  == 'X-API-Key'
        assert req.api_key_value == ''
