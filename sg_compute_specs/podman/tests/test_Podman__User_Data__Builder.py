# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Podman: tests for Podman__User_Data__Builder
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.podman.service.Podman__User_Data__Builder                     import (Podman__User_Data__Builder,
                                                                                              PLACEHOLDERS            ,
                                                                                              USER_DATA_TEMPLATE       )


class test_Podman__User_Data__Builder(TestCase):

    def setUp(self):
        self.builder = Podman__User_Data__Builder()

    def test_render__starts_with_shebang(self):
        result = self.builder.render('fast-fermi', 'eu-west-2')
        assert result.startswith('#!/usr/bin/env bash')

    def test_render__installs_podman(self):
        result = self.builder.render('fast-fermi', 'eu-west-2')
        assert 'dnf install -y podman' in result

    def test_render__enables_podman_socket(self):
        result = self.builder.render('fast-fermi', 'eu-west-2')
        assert 'podman.socket' in result

    def test_render__enables_ssm_agent(self):
        result = self.builder.render('fast-fermi', 'eu-west-2')
        assert 'amazon-ssm-agent' in result

    def test_render__embeds_stack_name_and_region(self):
        result = self.builder.render('fast-fermi', 'eu-west-2')
        assert 'fast-fermi' in result
        assert 'eu-west-2'  in result

    def test_placeholders_locked(self):
        assert PLACEHOLDERS == ('stack_name', 'region', 'log_file', 'shutdown_line')

    def test_template_has_all_placeholders(self):
        for p in PLACEHOLDERS:
            assert f'{{{p}}}' in USER_DATA_TEMPLATE

    def test_render__shutdown_timer_included_when_max_hours_set(self):
        result = self.builder.render('fast-fermi', 'eu-west-2', max_hours=2)
        assert 'shutdown -h +120' in result

    def test_render__no_shutdown_when_max_hours_zero(self):
        result = self.builder.render('fast-fermi', 'eu-west-2', max_hours=0)
        assert 'shutdown -h' not in result
        assert 'no auto-terminate' in result

    def test_schema__default_max_hours_is_one(self):
        from sg_compute_specs.podman.schemas.Schema__Podman__Create__Request import Schema__Podman__Create__Request
        assert Schema__Podman__Create__Request().max_hours == 1
