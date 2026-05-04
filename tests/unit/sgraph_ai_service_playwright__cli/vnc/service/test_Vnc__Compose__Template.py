# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Vnc__Compose__Template
# Locks the placeholder contract + canonical container / network names.
# Caddy replaced nginx in the v0.1.118 caddy slice.
# ═══════════════════════════════════════════════════════════════════════════════

import re

from unittest                                                                       import TestCase

from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Compose__Template           import (CHROMIUM_IMAGE       ,
                                                                                              COMPOSE_TEMPLATE     ,
                                                                                              MITMPROXY_IMAGE      ,
                                                                                              PLACEHOLDERS         ,
                                                                                              Vnc__Compose__Template)


class test_Vnc__Compose__Template(TestCase):

    def setUp(self):
        self.tpl = Vnc__Compose__Template()

    def test_render__substitutes_default_images(self):
        out = self.tpl.render()
        assert CHROMIUM_IMAGE  in out
        assert MITMPROXY_IMAGE in out

    def test_render__custom_images(self):
        out = self.tpl.render(chromium_image='lscr.io/linuxserver/chromium:r2024',
                              mitmproxy_image='mitmproxy/mitmproxy:11.0.0')
        assert 'chromium:r2024'      in out
        assert 'mitmproxy:11.0.0'    in out

    def test_render__no_placeholders_leaked(self):
        out      = self.tpl.render()
        leftover = re.findall(r'\{([a-z_]+)\}', out)
        assert leftover == []

    def test_render__includes_canonical_container_names(self):
        out = self.tpl.render()
        assert 'container_name: sg-chromium' in out
        assert 'container_name: sg-caddy'    in out
        assert 'container_name: sg-mitmproxy' in out

    def test_render__caddy_builds_locally_from_dockerfile(self):                     # No registry image — built at boot from /opt/sg-vnc/caddy/Dockerfile
        out = self.tpl.render()
        assert 'context: /opt/sg-vnc/caddy' in out
        assert 'sg-vnc/caddy:local'         in out                                   # Local image tag — survives compose restart

    def test_render__shared_network_named_sg_net(self):
        out = self.tpl.render()
        assert '- sg-net' in out
        assert 'sg-net:'  in out

    def test_render__chromium_uses_mitmproxy_as_proxy(self):
        out = self.tpl.render()
        assert 'HTTPS_PROXY=http://mitmproxy:8080' in out
        assert 'HTTP_PROXY=http://mitmproxy:8080'  in out

    def test_render__chromium_only_browser_flag(self):                              # N2 — chromium-only at runtime
        assert 'CHROME_CLI=--browser=chromium' in self.tpl.render()

    def test_render__exposes_only_443(self):                                        # 8080 is loopback; 8081 internal (proxied via Caddy /mitmweb/)
        out = self.tpl.render()
        assert '"443:443"' in out
        assert '8080:8080' not in out
        assert '8081:8081' not in out

    def test_render__no_password_in_compose(self):                                  # Operator credentials live in /opt/sg-vnc/caddy/users.json (bcrypt) on the host
        out = self.tpl.render()
        assert 'password'   not in out.lower()                                      # No password leaked anywhere

    def test_render__mitmproxy_command_drops_proxyauth(self):                       # Caddy now gates :8081 at /mitmweb/; mitmproxy --proxyauth on :8080 dropped (docker-network-only)
        out = self.tpl.render()
        assert '--proxyauth' not in out
        assert '--scripts=/opt/sg-vnc/interceptors/runtime/active.py' in out

    def test_render__caddy_mounts_required_files(self):
        out = self.tpl.render()
        assert '/opt/sg-vnc/caddy/Caddyfile:/etc/caddy/Caddyfile:ro,z'   in out
        assert '/opt/sg-vnc/caddy/users.json:/etc/caddy/users.json:ro,z' in out
        assert '/opt/sg-vnc/caddy/jwt-secret:/etc/caddy/jwt-secret:ro,z' in out

    def test_template_placeholders_match_PLACEHOLDERS_constant(self):
        in_template = set(re.findall(r'\{([a-z_]+)\}', COMPOSE_TEMPLATE))
        assert in_template == set(PLACEHOLDERS)
