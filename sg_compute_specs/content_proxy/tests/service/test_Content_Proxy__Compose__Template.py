# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: compose template render tests
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Edge                  import Enum__Content_Proxy__Edge
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Proxy__Tool           import Enum__Content_Proxy__Proxy__Tool
from sg_compute_specs.content_proxy.service.Content_Proxy__Compose__Template         import (Content_Proxy__Compose__Template,
                                                                                             PLACEHOLDERS, browser_block)


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

    def test_only_ext_allows_global_clients(self):
        # mitmproxy blocks public-IP ('global') clients by default → a remote browser is killed.
        # The ext proxy is internet-facing, so it must disable block_global; the int proxy only
        # serves docker-network (private-IP) clients, so it must NOT carry the override.
        ext_block = self.yaml.split('mitmproxy-ext:')[1]
        int_block = self.yaml.split('mitmproxy-int:')[1].split('mitmproxy-ext:')[0]
        assert 'block_global=false' in ext_block
        assert 'block_global'   not in int_block

    def test_secrets_are_env_refs_not_literals(self):
        assert '${CONTENT_PROXY__PROXYAUTH_USER}' in self.yaml
        assert '${CONTENT_PROXY__PROXYAUTH_PASS}' in self.yaml
        assert '${FASTAPI_API_KEY_VALUE}'         in self.yaml
        assert 'demo:demo' not in self.yaml                                         # no baked creds

    def test_playwright_proxied_to_int_with_ignore_https(self):
        assert 'SG_PLAYWRIGHT__DEFAULT_PROXY_URL=http://mitmproxy-int:8080' in self.yaml
        assert 'SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS=true'      in self.yaml             # Page__Factory only reads the SG_PLAYWRIGHT__-prefixed name; the bare form is silently ignored → ERR_CERT_AUTHORITY_INVALID through mitmproxy
        assert '- IGNORE_HTTPS_ERRORS=true'               not in self.yaml             # guard the prefix-less typo that disabled ignore_https_errors

    def test_vault_app_reverse_proxy_and_port(self):
        assert 'FAST_API__REVERSE_PROXY__ROUTES=pw=http://sg-playwright:8000' in self.yaml
        assert '"443:8080"' in self.yaml                                            # NONE default: host 443 → container 8080 (plain HTTP)
        assert 'command: ["python", "-m", "sg_overrides.serve_with_proxy"]' in self.yaml   # custom entrypoint mounts /pw
        assert './overrides:/app/sg_overrides:ro' in self.yaml                      # runtime-injected override package
        assert 'cert-init'  not in self.yaml                                        # no cert sidecar for NONE
        assert 'vault_certs' not in self.yaml

    def test_self_signed_tls(self):
        from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls import Enum__Content_Proxy__Tls
        yaml = Content_Proxy__Compose__Template().render(tls=Enum__Content_Proxy__Tls.SELF_SIGNED)
        assert '"443:443"' in yaml and '"443:8080"' not in yaml                     # vault terminates TLS on 443
        assert 'FAST_API__TLS__ENABLED=true' in yaml
        assert 'cp-cert-init' in yaml and 'SG__CERT_INIT__MODE=self-signed' in yaml
        assert 'vault_certs:/certs:ro' in yaml                                      # vault reads the cert (ro)
        assert '\nvolumes:\n  vault_certs:' in yaml                                 # named volume declared
        assert '"80:80"' not in yaml                                                # self-signed = offline, no ACME port

    def test_letsencrypt_ip_tls(self):
        from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Tls import Enum__Content_Proxy__Tls
        yaml = Content_Proxy__Compose__Template().render(tls=Enum__Content_Proxy__Tls.LETSENCRYPT)
        assert 'SG__CERT_INIT__MODE=letsencrypt-ip' in yaml
        assert '"80:80"' in yaml                                                    # http-01 challenge port
        assert 'SG__CERT_INIT__ACME_PROD=${SG__CERT_INIT__ACME_PROD:-true}' in yaml # IP certs need LE prod

    def test_mitm_service_gets_aws_creds_from_env_file(self):
        mitm_block = self.yaml.split('mitm-service:')[1].split('mitmproxy-int:')[0]
        for var in ('AWS_ACCOUNT_ID', 'AWS_DEFAULT_REGION', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                    'CACHE__SERVICE__BUCKET_NAME'):
            assert f'- {var}=${{{var}:-}}\n' in mitm_block, var                      # interpolated from .env (single source), empty default
        assert 'AWS_SECRET_ACCESS_KEY=sk' not in mitm_block                         # never a baked literal value

    def test_mitm_service_on_docker_network_only(self):
        mitm_block = self.yaml.split('mitm-service:')[1].split('mitmproxy-int:')[0]
        assert 'ports:' not in mitm_block                                          # :10011 net-local, never published

    def test_ca_dir_mounted_writable_into_both_proxies(self):
        assert self.yaml.count(':/home/mitmproxy/.mitmproxy\n') == 2                 # rw — mitmproxy self-generates its CA
        assert '/home/mitmproxy/.mitmproxy:ro' not in self.yaml

    def test_interceptors_mount_local_default_points_at_real_dir(self):
        assert self.yaml.count('../../interceptors:/interceptors:ro') == 2          # committed/local: two levels up

    def test_interceptors_mount_ec2_override(self):
        from sg_compute_specs.content_proxy.service.Content_Proxy__Compose__Template import INTERCEPTORS_MOUNT__EC2
        yaml = Content_Proxy__Compose__Template().render(interceptors_mount=INTERCEPTORS_MOUNT__EC2)
        assert yaml.count('./interceptors:/interceptors:ro') == 2
        assert '../../interceptors' not in yaml

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
                                'int_command', 'ext_command', 'interceptors_mount', 'browser_block',
                                'vault_block', 'cert_init_block', 'edge_block', 'volumes_block')


class test_browser_fleet(TestCase):

    def test_browser_block_zero_is_empty(self):                                      # count<=0 → nothing (committed local compose unchanged)
        assert browser_block(0)  == ''
        assert browser_block(-1) == ''

    def test_browser_block_renders_n_services_on_our_image(self):
        block = browser_block(2)
        assert 'cp-browser-1:' in block and 'cp-browser-2:' in block                 # exactly the fleet
        assert 'cp-browser-3:' not in block
        assert block.count('image: diniscruz/sg-playwright-vnc') == 2                # the image WE control — never jlesage
        assert block.count('SG_PLAYWRIGHT__DEFAULT_PROXY_URL=http://mitmproxy-int:8080') == 2  # launch-time proxy (no user.js / profile poking)
        assert block.count('SG_PLAYWRIGHT__IGNORE_HTTPS_ERRORS=true') == 2           # mitmproxy CA handled in-service (no certutil)
        assert block.count('SG_PLAYWRIGHT__AUTOSTART_BROWSER=chromium') == 2         # headed browser opens on the noVNC desktop at boot
        assert '${FAST_API__AUTH__API_KEY__VALUE}' in block                          # same access token as cp-sg-playwright
        assert block.count('/certs:ro') == 2                                         # mitmproxy CA mounted read-only → install-ca-trust gives a padlock instead of "Not secure"
        assert 'ports:'   not in block                                               # :6080 never published — the edge fronts it
        assert block.count('- mitmproxy-int') == 2                                   # depends_on the internal proxy

    def test_browser_engine_choice(self):
        assert browser_block(1, 'firefox').count('SG_PLAYWRIGHT__AUTOSTART_BROWSER=firefox') == 1

    def test_render_with_browsers_injects_fleet_after_playwright(self):
        yaml = Content_Proxy__Compose__Template().render(browser_count=2,
                                                         edge=Enum__Content_Proxy__Edge.CADDY)
        assert 'cp-browser-1:' in yaml and 'cp-browser-2:' in yaml
        assert yaml.index('sg-playwright:') < yaml.index('cp-browser-1:')            # fleet after the sg-playwright block
        assert yaml.index('cp-browser-2:') < yaml.index('vault-app:')                # …and before the vault/edge blocks

    def test_default_render_has_no_browser_containers(self):
        yaml = Content_Proxy__Compose__Template().render()                           # browser_count defaults to 0
        assert 'cp-firefox' not in yaml and 'cp-browser' not in yaml
