# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Vscode__User_Data__Builder tests
# Asserts on rendered cloud-init content — no AWS, no boot.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.vscode.enums.Enum__Vscode__Distribution  import Enum__Vscode__Distribution
from sg_compute_specs.vscode.enums.Enum__Vscode__Ingress       import Enum__Vscode__Ingress
from sg_compute_specs.vscode.service.Vscode__User_Data__Builder import Vscode__User_Data__Builder


class test_Vscode__User_Data__Builder(TestCase):

    def render(self, **kw) -> str:
        defaults = dict(stack_name='brave-fermi', region='eu-west-2',
                        password='s3cret-pw', max_hours=2.0,
                        distribution=Enum__Vscode__Distribution.CODE_SERVER)
        defaults.update(kw)
        return Vscode__User_Data__Builder().render(**defaults)

    def test_shebang_and_base(self):
        ud = self.render()
        assert ud.startswith('#!/usr/bin/env bash')
        assert 'set -euo pipefail'           in ud
        assert 'hostnamectl set-hostname brave-fermi' in ud

    def test_auto_terminate_timer(self):
        ud = self.render(max_hours=2.0)
        assert 'systemd-run --on-active=7200s' in ud           # 2h → 7200s, set before failable work

    def test_docker_and_code_server(self):
        ud = self.render(password='s3cret-pw')
        assert 'dnf install -y docker'        in ud
        assert 'codercom/code-server:latest'  in ud
        assert '127.0.0.1:8443:8080'          in ud
        assert 'PASSWORD=s3cret-pw'           in ud

    def test_footer_boot_ok(self):
        ud = self.render()
        assert 'touch /var/lib/sg-compute-boot-ok' in ud
        assert 'vscode boot complete'              in ud

    def test_ssm_mode_has_no_caddy(self):
        ud = self.render(ingress=Enum__Vscode__Ingress.SSM_FORWARD)
        assert 'caddy'              not in ud.lower()
        assert 'docker network'     not in ud
        assert '127.0.0.1:8443:8080' in ud                       # loopback-only publish

    def test_public_mode_adds_network_and_caddy(self):
        ud = self.render(ingress=Enum__Vscode__Ingress.PUBLIC_HTTPS)
        assert 'docker network create vscode-net' in ud
        assert '--network vscode-net'             in ud          # code-server joins the net
        assert 'caddy:2-alpine'                   in ud
        assert '-p 443:443'                       in ud
        assert '127.0.0.1:8443:8080'              in ud          # still loopback-published → forward/health work
        assert 'tls internal'                     in ud          # no domain → self-signed

    def test_public_mode_with_domain_uses_real_cert(self):
        ud = self.render(ingress=Enum__Vscode__Ingress.PUBLIC_HTTPS, domain='vsc.example.com')
        assert 'vsc.example.com {'                in ud          # Caddy site block → automatic Let's Encrypt
        assert 'tls internal'                 not in ud

    def test_serve_web_is_host_process_no_docker(self):
        ud = self.render(distribution=Enum__Vscode__Distribution.SERVE_WEB)
        assert 'code serve-web'             in ud
        assert 'code-serve-web.service'     in ud
        assert 'dnf install -y docker'  not in ud               # serve-web runs on the host, not in Docker
        assert 'codercom/code-server'   not in ud
        assert 'caddy'              not in ud.lower()

