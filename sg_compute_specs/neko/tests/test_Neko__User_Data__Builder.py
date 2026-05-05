# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Neko: tests for Neko__User_Data__Builder
# Pure template rendering — no AWS calls, no network.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.neko.service.Neko__User_Data__Builder                         import (LOG_FILE               ,
                                                                                             NEKO_IMAGE             ,
                                                                                             PLACEHOLDERS           ,
                                                                                             WEBRTC_PORT_FROM       ,
                                                                                             WEBRTC_PORT_TO         ,
                                                                                             Neko__User_Data__Builder)


class test_Neko__User_Data__Builder(TestCase):

    def setUp(self):
        self.builder = Neko__User_Data__Builder()

    def _render(self, **overrides):
        defaults = dict(stack_name      = 'happy-turing'  ,
                        region          = 'eu-west-2'     ,
                        admin_password  = 'admin-pass'    ,
                        member_password = 'member-pass'   )
        defaults.update(overrides)
        return self.builder.render(**defaults)

    def test_placeholders_tuple_locked(self):
        assert 'stack_name'      in PLACEHOLDERS
        assert 'region'          in PLACEHOLDERS
        assert 'caddyfile'       in PLACEHOLDERS
        assert 'compose_yaml'    in PLACEHOLDERS
        assert 'sidecar_section' in PLACEHOLDERS
        assert len(PLACEHOLDERS) == 11

    def test_render_returns_string(self):
        result = self._render()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_shebang_is_bash(self):
        result = self._render()
        assert result.startswith('#!/usr/bin/env bash')

    def test_render_contains_stack_name(self):
        result = self._render(stack_name='bold-curie')
        assert 'bold-curie' in result

    def test_render_contains_region(self):
        result = self._render(region='us-east-1')
        assert 'us-east-1' in result

    def test_render_contains_log_file(self):
        result = self._render()
        assert LOG_FILE in result

    def test_render_contains_neko_image(self):
        result = self._render()
        assert NEKO_IMAGE in result

    def test_render_contains_webrtc_ports(self):
        result = self._render()
        assert str(WEBRTC_PORT_FROM) in result
        assert str(WEBRTC_PORT_TO)   in result

    def test_render_fetches_public_ip_from_metadata(self):
        result = self._render()
        assert '169.254.169.254' in result

    def test_render_generates_self_signed_cert(self):
        result = self._render()
        assert 'openssl' in result
