# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Routes__Vault_Publish (TestClient, no mocks)
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from osbot_fast_api.api.Fast_API                         import Fast_API

from vault_publish.fast_api.Routes__Vault_Publish        import Routes__Vault_Publish
from vault_publish.schemas.Enum__Vault_App__Runtime      import Enum__Vault_App__Runtime
from vault_publish.schemas.Enum__Vault_App__Type         import Enum__Vault_App__Type
from vault_publish.schemas.Safe_Str__Manifest__Path      import Safe_Str__Manifest__Path
from vault_publish.schemas.Schema__Vault_App__Manifest   import Schema__Vault_App__Manifest
from vault_publish.service.Manifest__Verifier__In_Memory import Manifest__Verifier__In_Memory
from vault_publish.service.Publish__Service              import Publish__Service
from vault_publish.service.Slug__Resolver__In_Memory     import Slug__Resolver__In_Memory
from vault_publish.service.Vault__Fetcher__In_Memory     import Vault__Fetcher__In_Memory


def _service() -> Publish__Service:
    return Publish__Service(slug_resolver     = Slug__Resolver__In_Memory()    ,
                            vault_fetcher     = Vault__Fetcher__In_Memory()    ,
                            manifest_verifier = Manifest__Verifier__In_Memory())


def _client(service: Publish__Service):
    app = Fast_API()
    app.setup()
    app.add_routes(Routes__Vault_Publish, service=service)
    return app.client()


def _seed_vault(service: Publish__Service, raw_slug: str, key_ref: str) -> None:
    service.register(raw_slug, 'owner-1', key_ref)
    manifest   = Schema__Vault_App__Manifest(app_type     = Enum__Vault_App__Type.STATIC_SITE  ,
                                             runtime      = Enum__Vault_App__Runtime.STATIC    ,
                                             content_root = Safe_Str__Manifest__Path('public') ,
                                             health_path  = Safe_Str__Manifest__Path('healthz'))
    slug       = service.slug_validator.to_slug(raw_slug)
    folder_ref = service.slug_resolver.resolve(slug)
    signature  = service.manifest_verifier.sign(manifest, key_ref)
    service.vault_fetcher.publish(folder_ref, manifest, signature)


class test_Routes__Vault_Publish(TestCase):

    # ── POST /register ───────────────────────────────────────────────────────

    def test_register_success_200(self):
        resp = _client(_service()).post('/vault-publish/register',
                                        json={'slug': 'sara-cv', 'owner_id': 'owner-1',
                                              'signing_public_key_ref': 'key-ref-1'})
        assert resp.status_code        == 200
        data = resp.json()
        assert data['slug']            == 'sara-cv'
        assert data['registered']      is True
        assert data['url']             == 'https://sara-cv.sgraph.app/'

    def test_register_invalid_slug_400(self):
        resp = _client(_service()).post('/vault-publish/register',
                                        json={'slug': 'a--b', 'owner_id': 'o', 'signing_public_key_ref': 'k'})
        assert resp.status_code == 400
        assert resp.json()['detail']['error_code'] == 'double-hyphen'

    def test_register_duplicate_409(self):
        client = _client(_service())
        body   = {'slug': 'sara-cv', 'owner_id': 'o', 'signing_public_key_ref': 'k'}
        client.post('/vault-publish/register', json=body)
        resp = client.post('/vault-publish/register', json=body)
        assert resp.status_code == 409
        assert resp.json()['detail']['error_code'] == 'slug-taken'

    # ── GET /status ──────────────────────────────────────────────────────────

    def test_status_unregistered(self):
        resp = _client(_service()).get('/vault-publish/status/sara-cv')
        assert resp.status_code == 200
        assert resp.json()['registered'] is False

    def test_status_registered(self):
        service = _service()
        service.register('sara-cv', 'owner-1', 'key-ref-1')
        resp = _client(service).get('/vault-publish/status/sara-cv')
        assert resp.status_code == 200
        assert resp.json()['registered'] is True

    # ── GET /list ────────────────────────────────────────────────────────────

    def test_list_returns_slugs(self):
        service = _service()
        service.register('sara-cv', 'owner-1', 'key-ref-1')
        resp = _client(service).get('/vault-publish/list')
        assert resp.status_code == 200
        assert resp.json()['slugs'] == ['sara-cv']

    # ── POST /wake ───────────────────────────────────────────────────────────

    def test_wake_cold_returns_started_warming(self):
        service = _service()
        _seed_vault(service, 'sara-cv', 'key-ref-1')
        resp = _client(service).post('/vault-publish/wake', json={'slug': 'sara-cv'})
        assert resp.status_code == 200
        data = resp.json()
        assert data['outcome'] == 'started'
        assert data['warming'] is True

    def test_wake_invalid_slug_is_200_with_rejection(self):                  # wake never raises
        resp = _client(_service()).post('/vault-publish/wake', json={'slug': 'a--b'})
        assert resp.status_code == 200
        assert resp.json()['outcome'] == 'rejected-invalid-slug'

    def test_wake_not_registered_is_200_with_rejection(self):
        resp = _client(_service()).post('/vault-publish/wake', json={'slug': 'sara-cv'})
        assert resp.status_code == 200
        assert resp.json()['outcome'] == 'rejected-not-registered'

    # ── POST /resolve ────────────────────────────────────────────────────────

    def test_resolve_success(self):
        service = _service()
        _seed_vault(service, 'sara-cv', 'key-ref-1')
        resp = _client(service).post('/vault-publish/resolve', json={'slug': 'sara-cv'})
        assert resp.status_code == 200
        assert resp.json()['app_type'] == 'static-site'

    def test_resolve_vault_not_found_404(self):
        service = _service()
        service.register('sara-cv', 'owner-1', 'key-ref-1')
        resp = _client(service).post('/vault-publish/resolve', json={'slug': 'sara-cv'})
        assert resp.status_code == 404
        assert resp.json()['detail']['error_code'] == 'vault-not-found'

    # ── DELETE /unpublish ────────────────────────────────────────────────────

    def test_unpublish_removes_slug(self):
        service = _service()
        service.register('sara-cv', 'owner-1', 'key-ref-1')
        client  = _client(service)
        resp    = client.request('DELETE', '/vault-publish/unpublish/sara-cv')
        assert resp.status_code == 200
        assert resp.json()['unpublished'] is True
        assert client.get('/vault-publish/status/sara-cv').json()['registered'] is False

    # ── GET /health ──────────────────────────────────────────────────────────

    def test_health_returns_four_layers(self):
        resp = _client(_service()).get('/vault-publish/health')
        assert resp.status_code == 200
        data = resp.json()
        for layer in ('dns_ok', 'cert_ok', 'distribution_ok', 'waker_ok'):
            assert layer in data
