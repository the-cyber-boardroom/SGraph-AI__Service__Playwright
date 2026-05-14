# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Playwright__Compose__Template
# Pure rendering — no AWS, no network calls. Verifies the compose YAML
# contains the expected strings with and without --with-mitmproxy.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                    import TestCase

from sgraph_ai_service_playwright__cli.playwright.service.Playwright__Compose__Template import (
    Playwright__Compose__Template, PLACEHOLDERS, SG_PLAYWRIGHT_IMAGE, MITMPROXY_IMAGE)


class test_Playwright__Compose__Template(TestCase):

    def setUp(self):
        self.template = Playwright__Compose__Template()

    def test__render__without_mitmproxy__contains_expected_strings(self):
        yaml = self.template.render(image_tag='v1.2.3', api_key='test-key-abc')
        assert f'{SG_PLAYWRIGHT_IMAGE}:v1.2.3'          in yaml
        assert 'FAST_API__AUTH__API_KEY__VALUE=test-key-abc' in yaml
        assert '8000:8000'                               in yaml
        assert 'sg-net'                                  in yaml
        assert 'restart: unless-stopped'                 in yaml

    def test__render__without_mitmproxy__no_mitmproxy_block(self):
        yaml = self.template.render(image_tag='latest', api_key='k')
        assert 'mitmproxy'                               not in yaml
        assert 'SG_PLAYWRIGHT__DEFAULT_PROXY_URL'        not in yaml
        assert 'SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS'      not in yaml
        assert 'depends_on'                              not in yaml

    def test__render__with_mitmproxy__contains_proxy_env(self):
        yaml = self.template.render(image_tag='latest', api_key='k', with_mitmproxy=True)
        assert 'SG_PLAYWRIGHT__DEFAULT_PROXY_URL=http://mitmproxy:8080' in yaml
        assert 'SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS=1'                   in yaml

    def test__render__with_mitmproxy__contains_mitmproxy_service(self):
        yaml = self.template.render(image_tag='latest', api_key='k', with_mitmproxy=True)
        assert MITMPROXY_IMAGE                                           in yaml
        assert 'sg-mitmproxy'                                           in yaml
        assert 'mitmdump'                                               in yaml
        assert '--listen-port=8080'                                     in yaml
        assert '/opt/sg-playwright/interceptors'                        in yaml
        assert 'depends_on: [mitmproxy]'                                in yaml

    def test__render__with_mitmproxy__no_external_port_on_mitmproxy(self):
        yaml = self.template.render(image_tag='latest', api_key='k', with_mitmproxy=True)
        assert '8080:8080'                               not in yaml             # docker-network-only

    def test__render__default_image_tag_is_latest(self):
        yaml = self.template.render(api_key='k')
        assert f'{SG_PLAYWRIGHT_IMAGE}:latest'           in yaml

    def test__placeholders_constant_is_locked(self):
        assert 'sg_playwright_image'                     in PLACEHOLDERS
        assert 'image_tag'                               in PLACEHOLDERS
        assert 'api_key'                                 in PLACEHOLDERS
        assert 'mitmproxy_image'                         in PLACEHOLDERS
