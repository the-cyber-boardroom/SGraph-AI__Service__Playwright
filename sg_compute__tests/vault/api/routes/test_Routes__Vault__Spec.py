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
    app.add_routes(Routes__Vault__Spec, prefix='/api/vault', service=writer)   # must match production prefix; DO NOT remove prefix
    return app.client()


class test_Routes__Vault__Spec(TestCase):

    # ── PUT /spec/{spec_id}/{stack_id}/{handle} ──────────────────────────────

    def test_write__success_200(self):
        resp = _client().put('/api/vault/spec/firefox/_shared/credentials', content=b'secret')
        assert resp.status_code        == 200
        data = resp.json()
        assert data['spec_id']         == 'firefox'
        assert data['stack_id']        == '_shared'
        assert data['handle']          == 'credentials'
        assert data['bytes_written']   == len(b'secret')
        assert len(data['sha256'])     == 64
        assert data['vault_path']      == 'spec/firefox/_shared/credentials'

    def test_write__vault_path_has_spec_prefix(self):
        resp = _client().put('/api/vault/spec/firefox/my-stack/mitm-script', content=b'x')
        assert resp.status_code              == 200
        assert resp.json()['vault_path']     == 'spec/firefox/my-stack/mitm-script'

    def test_write__no_vault_returns_409(self):
        resp = _client(vault_attached=False).put(
            '/api/vault/spec/firefox/_shared/credentials', content=b'x')
        assert resp.status_code == 409
        assert resp.json()['detail']['error_code'] == 'no-vault-attached'

    def test_write__unknown_spec_returns_400(self):
        resp = _client().put('/api/vault/spec/bogus/_shared/credentials', content=b'x')
        assert resp.status_code == 400
        assert resp.json()['detail']['error_code'] == 'unknown-spec'

    def test_write__disallowed_handle_returns_400(self):
        resp = _client().put('/api/vault/spec/firefox/_shared/hacker-handle', content=b'x')
        assert resp.status_code == 400
        assert resp.json()['detail']['error_code'] == 'disallowed-handle'

    # ── GET /vault/spec/{spec_id} ────────────────────────────────────────────

    def test_list_spec__no_vault_returns_409(self):
        resp = _client(vault_attached=False).get('/api/vault/spec/firefox')
        assert resp.status_code == 409

    def test_list_spec__unknown_spec_returns_400(self):
        resp = _client().get('/api/vault/spec/no-such-spec')
        assert resp.status_code == 400
        assert resp.json()['detail']['error_code'] == 'unknown-spec'

    def test_list_spec__returns_receipts_envelope(self):
        resp = _client().get('/api/vault/spec/firefox')
        assert resp.status_code   == 200
        data = resp.json()
        assert 'receipts'         in data
        assert data['spec_id']    == 'firefox'

    # ── DELETE /vault/spec/{spec_id}/{stack_id}/{handle} ─────────────────────

    def test_delete__success_200(self):
        c = _client()
        c.put('/api/vault/spec/firefox/_shared/credentials', content=b'data')
        resp = c.delete('/api/vault/spec/firefox/_shared/credentials')
        assert resp.status_code        == 200
        data = resp.json()
        assert data['deleted']         is True
        assert data['spec_id']         == 'firefox'
        assert data['vault_path']      == 'spec/firefox/_shared/credentials'

    def test_delete__no_vault_returns_409(self):
        resp = _client(vault_attached=False).delete(
            '/api/vault/spec/firefox/_shared/credentials')
        assert resp.status_code == 409

    # ── round-trip: PUT then GET metadata ────────────────────────────────────

    def test_round_trip__write_then_metadata_sha256_matches(self):
        import hashlib
        blob = b'x' * 1024                                                  # 1 KB blob
        c    = _client()
        put_resp = c.put('/api/vault/spec/firefox/my-node/mitm-script', content=blob)
        assert put_resp.status_code == 200
        put_data = put_resp.json()
        assert put_data['bytes_written'] == 1024
        assert put_data['sha256']        == hashlib.sha256(blob).hexdigest()

        get_resp = c.get('/api/vault/spec/firefox/my-node/mitm-script/metadata')
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data['sha256']        == put_data['sha256']
        assert get_data['bytes_written'] == 1024
        assert get_data['vault_path']    == 'spec/firefox/my-node/mitm-script'

    def test_round_trip__metadata_404_before_write(self):
        resp = _client().get('/api/vault/spec/firefox/my-node/mitm-script/metadata')
        assert resp.status_code == 404

    def test_round_trip__list_contains_written_receipt(self):
        blob = b'hello'
        c    = _client()
        c.put('/api/vault/spec/firefox/_shared/credentials', content=blob)
        c.put('/api/vault/spec/firefox/_shared/profile',     content=blob)
        resp = c.get('/api/vault/spec/firefox')
        assert resp.status_code == 200
        data = resp.json()
        handles = {r['handle'] for r in data['receipts']}
        assert handles == {'credentials', 'profile'}

    def test_round_trip__delete_removes_metadata(self):
        c = _client()
        c.put('/api/vault/spec/firefox/_shared/credentials', content=b'secret')
        c.delete('/api/vault/spec/firefox/_shared/credentials')
        resp = c.get('/api/vault/spec/firefox/_shared/credentials/metadata')
        assert resp.status_code == 404
