# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — Content Proxy: Caddy edge PoC — template + compose-variant tests
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib                                                                        import Path
from unittest                                                                       import TestCase

import sg_compute_specs.content_proxy                                               as content_proxy_pkg
from sg_compute_specs.content_proxy.enums.Enum__Content_Proxy__Edge                  import Enum__Content_Proxy__Edge
from sg_compute_specs.content_proxy.service.Content_Proxy__Compose__Template         import Content_Proxy__Compose__Template
from sg_compute_specs.content_proxy.service.Content_Proxy__Edge__Template            import Content_Proxy__Edge__Template


class test_Content_Proxy__Edge__Template(TestCase):

    def setUp(self):
        self.caddy = Content_Proxy__Edge__Template().render()

    def test_routes_pw_to_playwright_with_auth(self):
        assert 'handle_path /pw/*' in self.caddy
        assert 'reverse_proxy sg-playwright:8000' in self.caddy
        assert 'header_up {$FAST_API__AUTH__API_KEY__NAME:x-api-key} {$SGRAPH_SEND__ACCESS_TOKEN}' in self.caddy  # env-driven name, never hardcoded
        assert 'header_up X-Forwarded-Prefix /pw' in self.caddy

    def test_root_to_vault_and_tls(self):
        assert 'reverse_proxy vault-app:8080' in self.caddy                          # everything else → vault (plain origin)
        assert 'tls internal' in self.caddy                                          # local: Caddy internal CA


class test_Content_Proxy__Edge__Template__browser_routes(TestCase):

    def test_no_browser_routes_by_default(self):
        caddy = Content_Proxy__Edge__Template().render()
        assert '/browser/' not in caddy                                              # browser_count defaults to 0 → no fleet routes

    def test_browser_count_emits_one_route_per_browser(self):
        caddy = Content_Proxy__Edge__Template().render(browser_count=2)
        assert 'handle_path /browser/1/*' in caddy                                   # engine-agnostic path (engine is a container env choice)
        assert 'handle_path /browser/2/*' in caddy
        assert 'reverse_proxy cp-browser-1:6080' in caddy                            # noVNC port on OUR image
        assert 'reverse_proxy cp-browser-2:6080' in caddy
        assert 'redir /browser/2 /browser/2/ 308' in caddy                           # bare path → canonical trailing slash
        assert 'path=browser/2/websockify' in caddy                                  # noVNC dials the SUB-PATH websocket (root-absolute /websockify would hit the vault catch-all)
        assert '/browser/2/vnc.html?path=browser/2/websockify' in caddy              # …reached via the in-handle @root redirect
        assert 'handle_path /browser/3/*' not in caddy

    def test_browser_routes_sit_above_the_catch_all(self):
        caddy = Content_Proxy__Edge__Template().render(browser_count=1)
        assert caddy.index('/browser/1') < caddy.index('handle {')                   # generated routes above the vault catch-all
        assert caddy.index('handle_path /pw/*') < caddy.index('/browser/1')          # …and below the /pw route

    def test_hostname_render_carries_browser_routes(self):
        caddy = Content_Proxy__Edge__Template().render(hostname='h.example.com', browser_count=1)
        assert 'h.example.com {' in caddy and 'handle_path /browser/1/*' in caddy

    def test_edge_auth_gates_each_browser(self):
        caddy = Content_Proxy__Edge__Template().render(browser_count=2, edge_auth=True)
        assert caddy.count('not header X-API-Key') == 3                              # one guard each: /pw + 2 browsers
        for i in (1, 2):
            blk = caddy.split(f'handle_path /browser/{i}/*')[1].split(f'redir /browser/{i} ')[0]  # split on the bare-path redir (not the in-handle @root one)
            assert 'not header X-API-Key' in blk and f'reverse_proxy cp-browser-{i}:6080' in blk


class test_Content_Proxy__Edge__Template__edge_auth(TestCase):

    def test_default_is_open_no_guard(self):                                         # opt-in: default render carries no gate
        caddy = Content_Proxy__Edge__Template().render()
        assert '@noauth'   not in caddy
        assert '/edge/auth' not in caddy

    def test_edge_auth_gates_pw(self):
        caddy = Content_Proxy__Edge__Template().render(edge_auth=True)
        pw = caddy.split('handle_path /pw/*')[1].split('redir /pw')[0]
        assert 'not header X-API-Key {$SGRAPH_SEND__ACCESS_TOKEN}'          in pw     # programmatic auth
        assert 'not header Cookie *cp_access={$SGRAPH_SEND__ACCESS_TOKEN}*' in pw     # browser cookie auth
        assert 'respond "unauthorized' in pw and '401' in pw
        assert 'reverse_proxy sg-playwright:8000' in pw                              # still proxies when authed

    def test_edge_auth_adds_cookie_bootstrap(self):
        caddy = Content_Proxy__Edge__Template().render(edge_auth=True)
        assert 'handle /edge/auth {' in caddy
        assert 'Set-Cookie "cp_access={http.request.uri.query.token}' in caddy        # ?token=… → cookie
        assert caddy.index('/edge/auth') < caddy.index('handle {\n\t\treverse_proxy vault-app')  # above the catch-all

    def test_edge_auth_off_is_byte_identical_to_before(self):                        # drift guard: opt-in must not change the open path
        assert Content_Proxy__Edge__Template().render(browser_count=2, edge_auth=False) \
            == Content_Proxy__Edge__Template().render(browser_count=2)


class test_compose_edge_caddy(TestCase):

    def setUp(self):
        self.yaml = Content_Proxy__Compose__Template().render(edge=Enum__Content_Proxy__Edge.CADDY)

    def test_caddy_service_owns_443(self):
        assert 'cp-caddy' in self.yaml
        assert './Caddyfile:/etc/caddy/Caddyfile:ro' in self.yaml
        assert '"443:443"' in self.yaml
        assert 'caddy_data:' in self.yaml                                            # named volume declared

    def test_vault_is_a_plain_origin(self):
        vault = self.yaml.split('vault-app:')[1].split('caddy:')[0]
        assert 'serve_with_proxy' not in vault                                       # no /pw runtime injection
        assert 'sg_overrides'    not in vault                                        # no override mount
        assert 'FAST_API__TLS__ENABLED' not in vault                                 # no vault TLS — edge does it
        assert 'ports:' not in vault                                                 # not published — caddy fronts it

    def test_no_cert_init_in_caddy_mode(self):
        assert 'cp-cert-init' not in self.yaml                                       # edge terminates TLS, not the vault

    def test_none_mode_unchanged(self):
        none = Content_Proxy__Compose__Template().render()
        assert 'cp-caddy' not in none and 'serve_with_proxy' in none                 # default path untouched


class test_committed_caddy_files_no_drift(TestCase):

    def test_committed_caddy_compose_and_caddyfile_match_templates(self):
        d         = Path(content_proxy_pkg.__file__).parent / 'docker' / 'compose'
        compose   = (d / 'docker-compose.caddy.yml').read_text()
        caddyfile = (d / 'Caddyfile').read_text()
        assert compose   == Content_Proxy__Compose__Template().render(edge=Enum__Content_Proxy__Edge.CADDY)
        assert caddyfile == Content_Proxy__Edge__Template().render()


class test_Content_Proxy__Edge__Template__internal_named_site(TestCase):

    def test_internal_site_is_named_not_bare_443(self):
        caddy = Content_Proxy__Edge__Template().render()
        assert 'localhost, 127.0.0.1 {' in caddy                                      # named site → internal cert provisioned (fixes tls internal error)
        assert ':443 {' not in caddy                                                  # bare :443 has no subject → handshake aborts


class test_Content_Proxy__Edge__Template__hostname(TestCase):

    def setUp(self):
        self.caddy = Content_Proxy__Edge__Template().render(hostname='my-stack.sg-compute.sgraph.ai',
                                                            acme_email='ops@example.com')

    def test_hostname_site_block(self):
        assert 'my-stack.sg-compute.sgraph.ai {' in self.caddy                        # the FQDN site → Caddy auto-ACME
        assert 'tls internal' not in self.caddy                                       # public cert, not internal CA
        assert 'localhost' not in self.caddy

    def test_acme_email_in_global_block(self):
        assert 'email ops@example.com' in self.caddy

    def test_routes_preserved(self):
        assert 'handle_path /pw/*'                in self.caddy
        assert 'reverse_proxy sg-playwright:8000' in self.caddy
        assert 'reverse_proxy vault-app:8080'     in self.caddy

    def test_no_email_when_blank(self):
        caddy = Content_Proxy__Edge__Template().render(hostname='h.example.com')
        assert 'email' not in caddy
        assert 'h.example.com {' in caddy


class test_compose_edge_caddy__hostname_ports(TestCase):

    def test_internal_publishes_only_443(self):
        yaml = Content_Proxy__Compose__Template().render(edge=Enum__Content_Proxy__Edge.CADDY)
        assert '"443:443"' in yaml and '"80:80"' not in yaml                          # tls internal → no ACME http-01 port (caddy is the only :80/:443 publisher)

    def test_hostname_publishes_80_and_443(self):
        yaml = Content_Proxy__Compose__Template().render(edge=Enum__Content_Proxy__Edge.CADDY,
                                                         hostname='h.sg-compute.sgraph.ai')
        assert '"80:80"' in yaml and '"443:443"' in yaml                              # auto-ACME needs :80 (http-01) + :443 (tls-alpn)
