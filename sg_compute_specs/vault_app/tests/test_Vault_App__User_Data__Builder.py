# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Vault_App__User_Data__Builder
# The reverse-proxy overrides must be written to disk before `compose up`, and
# only in the --with-playwright shape.
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.vault_app.service.Vault_App__User_Data__Builder import Vault_App__User_Data__Builder


class TestVaultAppUserDataBuilder:

    def _render(self, **kw):
        return Vault_App__User_Data__Builder().render(stack_name='vault-test', access_token='tok123', **kw)

    def test_with_playwright_writes_overrides(self):
        script = self._render(with_playwright=True)
        assert 'writing reverse-proxy overrides to /opt/vault-app/overrides' in script
        assert '/opt/vault-app/overrides/serve_with_proxy.py'               in script
        assert '/opt/vault-app/overrides/Fast_API__Reverse_Proxy.py'        in script

    def test_overrides_written_before_compose_up(self):
        script = self._render(with_playwright=True)
        assert script.index('reverse-proxy overrides written') < script.index('up -d')   # files on disk before the bind-mount is consumed

    def test_just_vault_has_no_overrides(self):
        script = self._render(with_playwright=False)
        assert 'sg_overrides'             not in script
        assert 'reverse-proxy overrides' not in script
