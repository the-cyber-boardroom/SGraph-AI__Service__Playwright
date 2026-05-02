# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — VNC: tests for Vnc__User_Data__Builder
# Pure template rendering — no AWS calls, no network.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.vnc.service.Vnc__Compose__Template                            import CHROMIUM_IMAGE, MITMPROXY_IMAGE
from sg_compute_specs.vnc.service.Vnc__User_Data__Builder                           import (LOG_FILE               ,
                                                                                             PLACEHOLDERS           ,
                                                                                             Vnc__User_Data__Builder)


SAMPLE_COMPOSE = 'services: {}'                                                     # Minimal stand-in; full compose tested separately


class test_Vnc__User_Data__Builder(TestCase):

    def setUp(self):
        self.builder = Vnc__User_Data__Builder()

    def _render(self, **overrides):
        defaults = dict(stack_name         = 'happy-turing'  ,
                        region             = 'eu-west-2'     ,
                        compose_yaml       = SAMPLE_COMPOSE  ,
                        interceptor_source = '# no-op\n'     ,
                        operator_password  = 'test-password' )
        defaults.update(overrides)
        return self.builder.render(**defaults)

    def test_placeholders_tuple_locked(self):
        assert 'stack_name'         in PLACEHOLDERS
        assert 'region'             in PLACEHOLDERS
        assert 'operator_password'  in PLACEHOLDERS
        assert 'interceptor_source' in PLACEHOLDERS
        assert 'caddy_jwt_secret'   in PLACEHOLDERS
        assert len(PLACEHOLDERS)    == 17

    def test_render_returns_string(self):
        result = self._render()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_contains_stack_name(self):
        result = self._render(stack_name='bold-curie')
        assert 'bold-curie' in result

    def test_render_contains_region(self):
        result = self._render(region='us-east-1')
        assert 'us-east-1' in result

    def test_render_contains_log_file(self):
        result = self._render()
        assert LOG_FILE in result

    def test_render_contains_interceptor_source(self):
        result = self._render(interceptor_source='# my interceptor\n')
        assert '# my interceptor' in result

    def test_render_contains_compose_yaml(self):
        result = self._render(compose_yaml=SAMPLE_COMPOSE)
        assert SAMPLE_COMPOSE in result

    def test_render_contains_caddy_install(self):
        result = self._render()
        assert 'xcaddy' in result

    def test_render_shebang_is_bash(self):
        result = self._render()
        assert result.startswith('#!/usr/bin/env bash')

    def test_render_interceptor_kind_default_is_none(self):
        result = self._render()
        assert 'kind=none' in result

    def test_render_interceptor_kind_explicit(self):
        result = self._render(interceptor_kind='name')
        assert 'kind=name' in result
