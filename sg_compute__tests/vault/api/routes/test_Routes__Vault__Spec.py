# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Vault__Spec (TestClient, no mocks)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from osbot_fast_api.api.Fast_API                                             import Fast_API

from sg_compute.core.spec.Spec__Registry                                     import Spec__Registry
from sg_compute.core.spec.schemas.Schema__Spec__Manifest__Entry              import Schema__Spec__Manifest__Entry
from sg_compute.vault.api.routes.Routes__Vault__Spec                         import Routes__Vault__Spec
from sg_compute.vault.service.Vault__Spec__Writer                            import Vault__Spec__Writer


def _client(vault_attached=True, spec_ids=('firefox',), handles=None):
    registry = Spec__Registry()
    for sid in spec_ids:
        registry.register(Schema__Spec__Manifest__Entry(spec_id=sid))
    if handles is None:
        handles = {'firefox': {'credentials', 'mitm-script', 'profile'}}
    writer = Vault__Spec__Writer(
        spec_registry         = registry,
        write_handles_by_spec = handles,
        vault_attached        = vault_attached,
    )
    app = Fast_API()
    app.setup()
    app.add_routes(Routes__Vault__Spec, service=writer)
    return app.client()


class test_Routes__Vault__Spec(TestCase):

    # ── PUT /spec/{spec_id}/{stack_id}/{handle} ──────────────────────────────

    def test_write__success_200(self):
        resp = _client().put('/vault/spec/firefox/_shared/credentials', content=b'secret')
        assert resp.status_code        == 200
        data = resp.json()
        assert data['spec_id']         == 'firefox'
        assert data['stack_id']        == '_shared'
        assert data['handle']          == 'credentials'
        assert data['bytes_written']   == len(b'secret')
        assert len(data['sha256'])     == 64
        assert data['vault_path']      == 'spec/firefox/_shared/credentials'

    def test_write__vault_path_has_spec_prefix(self):
        resp = _client().put('/vault/spec/firefox/my-stack/mitm-script', content=b'x')
        assert resp.status_code              == 200
        assert resp.json()['vault_path']     == 'spec/firefox/my-stack/mitm-script'

    def test_write__no_vault_returns_409(self):
        resp = _client(vault_attached=False).put(
            '/vault/spec/firefox/_shared/credentials', content=b'x')
        assert resp.status_code == 409
        assert resp.json()['detail']['error_code'] == 'no-vault-attached'

    def test_write__unknown_spec_returns_400(self):
        resp = _client().put('/vault/spec/bogus/_shared/credentials', content=b'x')
        assert resp.status_code == 400
        assert resp.json()['detail']['error_code'] == 'unknown-spec'

    def test_write__disallowed_handle_returns_400(self):
        resp = _client().put('/vault/spec/firefox/_shared/hacker-handle', content=b'x')
        assert resp.status_code == 400
        assert resp.json()['detail']['error_code'] == 'disallowed-handle'

    # ── GET /vault/spec/{spec_id} ────────────────────────────────────────────

    def test_list_spec__no_vault_returns_409(self):
        resp = _client(vault_attached=False).get('/vault/spec/firefox')
        assert resp.status_code == 409

    def test_list_spec__unknown_spec_returns_400(self):
        resp = _client().get('/vault/spec/no-such-spec')
        assert resp.status_code == 400
        assert resp.json()['detail']['error_code'] == 'unknown-spec'

    def test_list_spec__returns_receipts_envelope(self):
        resp = _client().get('/vault/spec/firefox')
        assert resp.status_code   == 200
        data = resp.json()
        assert 'receipts'         in data
        assert data['spec_id']    == 'firefox'

    # ── DELETE /vault/spec/{spec_id}/{stack_id}/{handle} ─────────────────────

    def test_delete__success_200(self):
        resp = _client().delete('/vault/spec/firefox/_shared/credentials')
        assert resp.status_code == 200

    def test_delete__no_vault_returns_409(self):
        resp = _client(vault_attached=False).delete(
            '/vault/spec/firefox/_shared/credentials')
        assert resp.status_code == 409
