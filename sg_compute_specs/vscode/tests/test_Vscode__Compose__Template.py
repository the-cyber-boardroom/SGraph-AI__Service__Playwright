# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode: Vscode__Compose__Template tests
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.vscode.enums.Enum__Vscode__Distribution  import Enum__Vscode__Distribution
from sg_compute_specs.vscode.service.Vscode__Compose__Template import Vscode__Compose__Template


class test_Vscode__Compose__Template(TestCase):

    def test_code_server_render(self):
        out = Vscode__Compose__Template().render(
            distribution=Enum__Vscode__Distribution.CODE_SERVER,
            password='pw-123', port=8443)
        assert 'codercom/code-server:latest' in out
        assert '127.0.0.1:8443:8080'         in out
        assert 'PASSWORD=pw-123'             in out
        assert 'docker run -d --name code-server' in out

    def test_serve_web_not_implemented_yet(self):
        with self.assertRaises(NotImplementedError):
            Vscode__Compose__Template().render(
                distribution=Enum__Vscode__Distribution.SERVE_WEB,
                password='pw', port=8443)

    def test_openvscode_not_implemented_yet(self):
        with self.assertRaises(NotImplementedError):
            Vscode__Compose__Template().render(
                distribution=Enum__Vscode__Distribution.OPENVSCODE_SERVER,
                password='pw', port=8443)
