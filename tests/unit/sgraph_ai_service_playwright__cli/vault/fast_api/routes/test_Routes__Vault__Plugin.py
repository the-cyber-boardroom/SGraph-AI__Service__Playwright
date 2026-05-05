# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Vault__Spec (via legacy shim path)
# Retargeted to sg_compute.vault in BV2.9. Shim alias kept for one release.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from osbot_fast_api.api.Fast_API                                             import Fast_API

from sg_compute.vault.api.routes.Routes__Vault__Spec                         import Routes__Vault__Spec
from sg_compute.vault.service.Vault__Spec__Writer                            import Vault__Spec__Writer

FIREFOX_HANDLES = {'credentials', 'mitm-script', 'profile'}


def _client(vault_attached=True):
    writer = Vault__Spec__Writer(
        write_handles_by_spec = {'firefox': FIREFOX_HANDLES},
        vault_attached        = vault_attached,
    )
    app = Fast_API()
    app.setup()
    app.add_routes(Routes__Vault__Spec, service=writer)
    return app.client()


class test_Routes__Vault__Plugin(TestCase):

    def test_write__success_200(self):
        resp = _client().put('/vault/spec/firefox/_shared/credentials',
                             content=b'secret-data')
        assert resp.status_code == 200
        data = resp.json()
        assert data['spec_id']      == 'firefox'
        assert data['stack_id']     == '_shared'
        assert data['handle']       == 'credentials'
        assert data['bytes_written'] == len(b'secret-data')
        assert len(data['sha256'])  == 64

    def test_write__vault_path_in_receipt(self):
        resp = _client().put('/vault/spec/firefox/my-stack/mitm-script',
                             content=b'mitm bytes')
        assert resp.status_code           == 200
        assert resp.json()['vault_path']  == 'spec/firefox/my-stack/mitm-script'

    def test_write__no_vault_returns_409(self):
        resp = _client(vault_attached=False).put(
            '/vault/spec/firefox/_shared/credentials', content=b'x')
        assert resp.status_code == 409
        assert resp.json()['detail']['error_code'] == 'no-vault-attached'

    def test_write__unknown_plugin_returns_400(self):
        resp = _client().put('/vault/spec/bogus/_shared/credentials', content=b'x')
        assert resp.status_code == 400
        assert resp.json()['detail']['error_code'] == 'unknown-spec'

    def test_write__disallowed_handle_returns_400(self):
        resp = _client().put('/vault/spec/firefox/_shared/hacker-handle', content=b'x')
        assert resp.status_code == 400
        assert resp.json()['detail']['error_code'] == 'disallowed-handle'

    def test_list__no_vault_returns_409(self):
        resp = _client(vault_attached=False).get('/vault/spec/firefox')
        assert resp.status_code == 409

    def test_list__unknown_plugin_returns_400(self):
        resp = _client().get('/vault/spec/no-such-plugin')
        assert resp.status_code == 400

    def test_list__returns_receipts_key(self):
        resp = _client().get('/vault/spec/firefox')
        assert resp.status_code      == 200
        data = resp.json()
        assert 'receipts' in data
        assert data['spec_id'] == 'firefox'

    def test_delete__success_200(self):
        resp = _client().delete('/vault/spec/firefox/_shared/credentials')
        assert resp.status_code == 200

    def test_delete__no_vault_returns_409(self):
        resp = _client(vault_attached=False).delete(
            '/vault/spec/firefox/_shared/credentials')
        assert resp.status_code == 409
