# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Vscode__Caddy__Template tests
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.vscode.service.Vscode__Caddy__Template import Vscode__Caddy__Template


class test_Vscode__Caddy__Template(TestCase):

    def test_caddyfile_internal_when_no_domain(self):
        cf = Vscode__Caddy__Template().render_caddyfile()
        assert ':443'                        in cf
        assert 'tls internal'                in cf
        assert 'reverse_proxy code-server:8080' in cf

    def test_caddyfile_domain_uses_auto_tls(self):
        cf = Vscode__Caddy__Template().render_caddyfile(domain='vscode.example.com')
        assert cf.startswith('vscode.example.com {')
        assert 'tls internal'                not in cf            # real hostname → automatic Let's Encrypt
        assert 'reverse_proxy code-server:8080' in cf

    def test_boot_block_writes_caddyfile_and_runs_caddy(self):
        block = Vscode__Caddy__Template().render_boot_block(network='vscode-net')
        assert 'caddy:2-alpine'              in block
        assert '--network vscode-net'        in block
        assert '-p 443:443'                  in block
        assert '/etc/caddy/Caddyfile'        in block
        assert 'tls internal'                in block
