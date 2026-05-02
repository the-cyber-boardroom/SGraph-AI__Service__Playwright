# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Vault__Plugin (TestClient, no mocks)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from osbot_fast_api.api.Fast_API                                                    import Fast_API

from sgraph_ai_service_playwright__cli.core.plugin.Plugin__Registry                import Plugin__Registry
from sgraph_ai_service_playwright__cli.firefox.plugin.Plugin__Manifest__Firefox    import Plugin__Manifest__Firefox
from sgraph_ai_service_playwright__cli.vault.fast_api.routes.Routes__Vault__Plugin  import Routes__Vault__Plugin
from sgraph_ai_service_playwright__cli.vault.service.Vault__Plugin__Writer          import Vault__Plugin__Writer


def _client(vault_attached: bool = True):
    registry          = Plugin__Registry()
    registry.manifests['firefox'] = Plugin__Manifest__Firefox()
    writer            = Vault__Plugin__Writer(plugin_registry=registry, vault_attached=vault_attached)
    app               = Fast_API()
    app.setup()
    app.add_routes(Routes__Vault__Plugin, service=writer)
    return app.client()


class test_Routes__Vault__Plugin(TestCase):

    # ── PUT /vault/plugin/{plugin_id}/{stack_id}/{handle} ────────────────────

    def test_write__success_200(self):
        resp = _client().put('/vault/plugin/firefox/_global/credentials',
                             content=b'secret-data')
        assert resp.status_code == 200
        data = resp.json()
        assert data['plugin_id']      == 'firefox'
        assert data['stack_id']       == '_global'
        assert data['handle']         == 'credentials'
        assert data['bytes_written']  == len(b'secret-data')
        assert len(data['sha256'])    == 64

    def test_write__vault_path_in_receipt(self):
        resp = _client().put('/vault/plugin/firefox/my-stack/mitm-script',
                             content=b'mitm bytes')
        assert resp.status_code           == 200
        assert resp.json()['vault_path']  == 'plugin/firefox/my-stack/mitm-script'

    def test_write__no_vault_returns_409(self):
        resp = _client(vault_attached=False).put(
            '/vault/plugin/firefox/_global/credentials', content=b'x')
        assert resp.status_code == 409
        assert resp.json()['detail']['error_code'] == 'no-vault-attached'

    def test_write__unknown_plugin_returns_400(self):
        resp = _client().put('/vault/plugin/bogus/_global/credentials', content=b'x')
        assert resp.status_code == 400
        assert resp.json()['detail']['error_code'] == 'unknown-plugin'

    def test_write__disallowed_handle_returns_400(self):
        resp = _client().put('/vault/plugin/firefox/_global/hacker-handle', content=b'x')
        assert resp.status_code == 400
        assert resp.json()['detail']['error_code'] == 'disallowed-handle'

    # ── GET /vault/plugin/{plugin_id} ────────────────────────────────────────

    def test_list__no_vault_returns_409(self):
        resp = _client(vault_attached=False).get('/vault/plugin/firefox')
        assert resp.status_code == 409

    def test_list__unknown_plugin_returns_400(self):
        resp = _client().get('/vault/plugin/no-such-plugin')
        assert resp.status_code == 400

    def test_list__returns_receipts_key(self):
        resp = _client().get('/vault/plugin/firefox')
        assert resp.status_code      == 200
        data = resp.json()
        assert 'receipts' in data
        assert data['plugin_id'] == 'firefox'

    # ── DELETE /vault/plugin/{plugin_id}/{stack_id}/{handle} ─────────────────

    def test_delete__success_200(self):
        resp = _client().delete('/vault/plugin/firefox/_global/credentials')
        assert resp.status_code == 200

    def test_delete__no_vault_returns_409(self):
        resp = _client(vault_attached=False).delete(
            '/vault/plugin/firefox/_global/credentials')
        assert resp.status_code == 409
