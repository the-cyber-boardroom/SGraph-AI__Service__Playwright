# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Firefox: tests for Firefox__User_Data__Builder
# Pure template rendering — no AWS calls, no network.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.firefox.service.Firefox__User_Data__Builder                   import (Firefox__User_Data__Builder ,
                                                                                             FIREFOX_IMAGE              ,
                                                                                             LOG_FILE                   ,
                                                                                             MITM_IMAGE                 ,
                                                                                             MITMWEB_PORT               ,
                                                                                             PLACEHOLDERS               ,
                                                                                             USER_DATA_TEMPLATE         ,
                                                                                             VIEWER_PORT                )


class test_Firefox__User_Data__Builder(TestCase):

    def setUp(self):
        self.builder = Firefox__User_Data__Builder()

    def _render(self, **overrides):
        defaults = dict(stack_name         = 'fast-fermi'          ,
                        region             = 'eu-west-2'           ,
                        password           = 'test-password-12345' ,
                        interceptor_source = '# no-op\n'           )
        defaults.update(overrides)
        return self.builder.render(**defaults)

    def test_placeholders_tuple_locked(self):
        expected = ('stack_name', 'region', 'log_file', 'firefox_dir', 'mitm_data_dir',
                    'app_data_dir', 'profile_dir', 'compose_file', 'compose_yaml',
                    'interceptor_file', 'interceptor_source', 'interceptor_kind',
                    'user_js_file', 'user_js', 'env_file', 'env_source',
                    'sidecar_section', 'shutdown_section')
        assert PLACEHOLDERS == expected

    def test_template_contains_all_placeholders(self):
        for p in PLACEHOLDERS:
            assert '{' + p + '}' in USER_DATA_TEMPLATE, f'missing placeholder: {p}'

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

    def test_render_contains_interceptor_source(self):
        result = self._render(interceptor_source='# my interceptor\n')
        assert '# my interceptor' in result

    def test_render_contains_firefox_image(self):
        result = self._render()
        assert FIREFOX_IMAGE in result

    def test_render_contains_mitm_image(self):
        result = self._render()
        assert MITM_IMAGE in result

    def test_render_interceptor_kind_default_is_none(self):
        result = self._render()
        assert 'kind=none' in result

    def test_render_interceptor_kind_explicit(self):
        result = self._render(interceptor_kind='name')
        assert 'kind=name' in result

    def test_render_viewer_port_in_compose(self):
        result = self._render()
        assert str(VIEWER_PORT) in result

    def test_render_mitmweb_port_in_compose(self):
        result = self._render()
        assert str(MITMWEB_PORT) in result

    def test_render_password_in_compose(self):
        result = self._render(password='super-secret-pw')
        assert 'super-secret-pw' in result

    def test_render_shutdown_section_included_by_default(self):
        result = self._render(max_hours=1)
        assert 'shutdown' in result.lower() or 'systemd-run' in result

    def test_render_no_shutdown_when_max_hours_zero(self):
        result = self._render(max_hours=0)
        assert 'systemd-run' not in result

    def test_firefox_image_constant(self):
        assert FIREFOX_IMAGE == 'jlesage/firefox'

    def test_mitm_image_constant(self):
        assert MITM_IMAGE == 'mitmproxy/mitmproxy'

    def test_viewer_port_constant(self):
        assert VIEWER_PORT == 443

    def test_mitmweb_port_constant(self):
        assert MITMWEB_PORT == 8081
