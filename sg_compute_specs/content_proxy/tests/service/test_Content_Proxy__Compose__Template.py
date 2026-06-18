# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: compose template render tests
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Proxy__Tool           import Enum__Content_Proxy__Proxy__Tool
from sg_compute_specs.content_proxy.service.Content_Proxy__Compose__Template         import (Content_Proxy__Compose__Template,
                                                                                             PLACEHOLDERS)


class test_Content_Proxy__Compose__Template(TestCase):

    def setUp(self):
        self.yaml = Content_Proxy__Compose__Template().render()

    def test_five_services_present(self):
        for svc in ('mitm-service', 'mitmproxy-int', 'mitmproxy-ext', 'sg-playwright', 'vault-app'):
            assert f'{svc}:' in self.yaml, svc

    def test_two_mitmproxies_run_the_same_interceptor(self):
        assert self.yaml.count('--scripts=/interceptors/active.py') == 2

    def test_only_ext_has_proxyauth(self):
        assert 'proxyauth=' in self.yaml                                            # ext has it
        # the int service block must NOT contain proxyauth
        int_block = self.yaml.split('mitmproxy-int:')[1].split('mitmproxy-ext:')[0]
        assert 'proxyauth' not in int_block

    def test_secrets_are_env_refs_not_literals(self):
        assert '${CONTENT_PROXY__PROXYAUTH_USER}' in self.yaml
        assert '${CONTENT_PROXY__PROXYAUTH_PASS}' in self.yaml
        assert '${FASTAPI_API_KEY_VALUE}'         in self.yaml
        assert 'demo:demo' not in self.yaml                                         # no baked creds

    def test_playwright_proxied_to_int_with_ignore_https(self):
        assert 'SG_PLAYWRIGHT__DEFAULT_PROXY_URL=http://mitmproxy-int:8080' in self.yaml
        assert 'IGNORE_HTTPS_ERRORS=true' in self.yaml

    def test_vault_app_reverse_proxy_and_443(self):
        assert 'FAST_API__REVERSE_PROXY__ROUTES=pw=http://sg-playwright:8000' in self.yaml
        assert '"443:443"' in self.yaml

    def test_mitm_service_on_docker_network_only(self):
        mitm_block = self.yaml.split('mitm-service:')[1].split('mitmproxy-int:')[0]
        assert 'ports:' not in mitm_block                                          # :10011 net-local, never published

    def test_ca_dir_mounted_into_both_proxies(self):
        assert self.yaml.count('/home/mitmproxy/.mitmproxy:ro') == 2

    def test_default_images(self):
        assert 'mitmproxy/mitmproxy:12.2.3'             in self.yaml
        assert 'diniscruz/mgraph-ai-service-mitmproxy'  in self.yaml
        assert 'diniscruz/sg-playwright'                in self.yaml
        assert 'diniscruz/sg-send-vault'                in self.yaml

    def test_image_override(self):
        yaml = Content_Proxy__Compose__Template().render(mitmproxy_image='mitmproxy/mitmproxy:10.4.2')
        assert 'mitmproxy/mitmproxy:10.4.2' in yaml

    def test_default_tool_is_mitmweb_with_flows_api(self):
        assert '- mitmweb'     in self.yaml                                          # default render = dev (TUI /flows)
        assert '--web-port=8081' in self.yaml

    def test_mitmdump_tool_is_headless(self):
        yaml = Content_Proxy__Compose__Template().render(
            proxy_tool=Enum__Content_Proxy__Proxy__Tool.MITMDUMP)
        assert '- mitmdump'   in yaml
        assert 'mitmweb'      not in yaml                                            # no web UI in prod
        assert '--web-port'   not in yaml
        assert yaml.count('--scripts=/interceptors/active.py') == 2                  # both proxies still run the interceptor
        assert 'proxyauth=' in yaml                                                  # ext still authed

    def test_placeholders_locked(self):
        assert PLACEHOLDERS == ('mitmproxy_image', 'mitm_service_image', 'playwright_image',
                                'vault_app_image', 'int_command', 'ext_command')
