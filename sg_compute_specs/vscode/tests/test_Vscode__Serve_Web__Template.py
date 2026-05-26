# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Vscode__Serve_Web__Template tests
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.vscode.service.Vscode__Serve_Web__Template import Vscode__Serve_Web__Template


class test_Vscode__Serve_Web__Template(TestCase):

    def test_render(self):
        out = Vscode__Serve_Web__Template().render(port=8443)
        assert 'code serve-web'             in out
        assert '--without-connection-token' in out          # tokenless on loopback — SSM is the gate
        assert '--port 8443'                in out
        assert 'cli-linux-x64'              in out          # official MS CLI download
        assert 'code-serve-web.service'     in out          # systemd unit → restarts on crash
        assert 'systemctl enable --now code-serve-web' in out
