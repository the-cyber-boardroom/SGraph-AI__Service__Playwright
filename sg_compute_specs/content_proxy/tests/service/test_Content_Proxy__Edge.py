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
        assert 'header_up X-API-Key {$SGRAPH_SEND__ACCESS_TOKEN}' in self.caddy      # auth injected at the edge
        assert 'header_up X-Forwarded-Prefix /pw' in self.caddy

    def test_root_to_vault_and_tls(self):
        assert 'reverse_proxy vault-app:8080' in self.caddy                          # everything else → vault (plain origin)
        assert 'tls internal' in self.caddy                                          # local: Caddy internal CA


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
