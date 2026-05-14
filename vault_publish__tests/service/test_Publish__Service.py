# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Publish__Service (no mocks, no patches — in-memory composition)
# The orchestrator end to end: register, status, list, unpublish, resolve and
# the full wake sequence including the security rejections.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from vault_publish.schemas.Enum__Publish__Error_Code     import Enum__Publish__Error_Code
from vault_publish.schemas.Enum__Slug__Error_Code        import Enum__Slug__Error_Code
from vault_publish.schemas.Enum__Instance__State         import Enum__Instance__State
from vault_publish.schemas.Enum__Vault_App__Runtime      import Enum__Vault_App__Runtime
from vault_publish.schemas.Enum__Vault_App__Type         import Enum__Vault_App__Type
from vault_publish.schemas.Enum__Wake__Outcome           import Enum__Wake__Outcome
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


def _manifest() -> Schema__Vault_App__Manifest:
    return Schema__Vault_App__Manifest(app_type     = Enum__Vault_App__Type.STATIC_SITE  ,
                                       runtime      = Enum__Vault_App__Runtime.STATIC    ,
                                       content_root = Safe_Str__Manifest__Path('public') ,
                                       health_path  = Safe_Str__Manifest__Path('healthz'))


def _seed_vault(service: Publish__Service, raw_slug: str, key_ref: str,
                manifest: Schema__Vault_App__Manifest = None) -> None:
    # register the slug, then publish a correctly-signed manifest at its derived
    # location so the full wake sequence can run.
    service.register(raw_slug, 'owner-1', key_ref)
    manifest   = manifest or _manifest()
    slug       = service.slug_validator.to_slug(raw_slug)
    folder_ref = service.slug_resolver.resolve(slug)
    signature  = service.manifest_verifier.sign(manifest, key_ref)
    service.vault_fetcher.publish(folder_ref, manifest, signature)


class test_Publish__Service(TestCase):

    # ── register ─────────────────────────────────────────────────────────────

    def test_register_success(self):
        response, error = _service().register('sara-cv', 'owner-1', 'key-ref-1')
        assert error is None
        assert response.registered      is True
        assert str(response.slug)        == 'sara-cv'
        assert str(response.url)         == 'https://sara-cv.sgraph.app/'

    def test_register_invalid_slug(self):
        response, error = _service().register('a--b', 'owner-1', 'key-ref-1')
        assert response is None
        assert error    == Enum__Slug__Error_Code.DOUBLE_HYPHEN

    def test_register_reserved_slug(self):
        response, error = _service().register('admin', 'owner-1', 'key-ref-1')
        assert response is None
        assert error    == Enum__Slug__Error_Code.RESERVED

    def test_register_duplicate_slug(self):
        service = _service()
        service.register('sara-cv', 'owner-1', 'key-ref-1')
        response, error = service.register('sara-cv', 'owner-2', 'key-ref-2')
        assert response is None
        assert error    == Enum__Publish__Error_Code.SLUG_TAKEN

    # ── status / list ────────────────────────────────────────────────────────

    def test_status_unregistered_slug(self):
        response, error = _service().status('sara-cv')
        assert error is None
        assert response.registered      is False
        assert response.instance_state  == Enum__Instance__State.UNKNOWN

    def test_status_registered_slug(self):
        service = _service()
        service.register('sara-cv', 'owner-1', 'key-ref-1')
        response, error = service.status('sara-cv')
        assert error is None
        assert response.registered is True

    def test_list_returns_sorted_slugs(self):
        service = _service()
        service.register('zeta-site', 'owner-1', 'key-ref-1')
        service.register('alpha-site', 'owner-1', 'key-ref-1')
        slugs = [str(s) for s in service.list().slugs]
        assert slugs == ['alpha-site', 'zeta-site']

    # ── unpublish ────────────────────────────────────────────────────────────

    def test_unpublish_removes_registration(self):
        service = _service()
        service.register('sara-cv', 'owner-1', 'key-ref-1')
        response, error = service.unpublish('sara-cv')
        assert error is None
        assert response.unpublished is True
        assert service.status('sara-cv')[0].registered is False

    def test_unpublish_unregistered_slug(self):
        response, error = _service().unpublish('sara-cv')
        assert error is None
        assert response.unpublished is False

    # ── resolve ──────────────────────────────────────────────────────────────

    def test_resolve_success(self):
        service = _service()
        _seed_vault(service, 'sara-cv', 'key-ref-1')
        response, error = service.resolve('sara-cv')
        assert error is None
        assert str(response.transfer_id) != ''
        assert response.app_type == Enum__Vault_App__Type.STATIC_SITE

    def test_resolve_vault_not_found(self):
        service = _service()
        service.register('sara-cv', 'owner-1', 'key-ref-1')                  # registered but no vault folder seeded
        response, error = service.resolve('sara-cv')
        assert response is None
        assert error    == Enum__Publish__Error_Code.VAULT_NOT_FOUND

    # ── wake — happy path ────────────────────────────────────────────────────

    def test_wake_cold_starts_instance(self):
        service = _service()
        _seed_vault(service, 'sara-cv', 'key-ref-1')
        response = service.wake('sara-cv')
        assert response.outcome        == Enum__Wake__Outcome.STARTED
        assert response.warming        is True
        assert response.instance_state == Enum__Instance__State.PENDING
        assert str(response.instance_id) != ''

    def test_wake_warm_is_already_running(self):
        service = _service()
        _seed_vault(service, 'sara-cv', 'key-ref-1')
        service.wake('sara-cv')
        service.instances.mark_ready(service.slug_validator.to_slug('sara-cv'))
        response = service.wake('sara-cv')
        assert response.outcome == Enum__Wake__Outcome.ALREADY_RUNNING
        assert response.warming is False

    def test_wake_provisions_control_plane(self):
        service = _service()
        _seed_vault(service, 'sara-cv', 'key-ref-1')
        service.wake('sara-cv')
        slug = service.slug_validator.to_slug('sara-cv')
        assert service.control_plane.provisioned_plan(slug) is not None

    # ── wake — rejections (nothing started) ──────────────────────────────────

    def test_wake_invalid_slug_rejected(self):
        response = _service().wake('a--b')
        assert response.outcome == Enum__Wake__Outcome.REJECTED_INVALID_SLUG
        assert response.warming is False

    def test_wake_not_registered_rejected(self):
        response = _service().wake('sara-cv')
        assert response.outcome == Enum__Wake__Outcome.REJECTED_NOT_REGISTERED

    def test_wake_vault_not_found_rejected(self):
        service = _service()
        service.register('sara-cv', 'owner-1', 'key-ref-1')                  # no vault folder seeded
        response = service.wake('sara-cv')
        assert response.outcome == Enum__Wake__Outcome.REJECTED_VAULT_NOT_FOUND

    def test_wake_unverified_manifest_rejected_and_nothing_started(self):
        service  = _service()
        manifest = _manifest()
        _seed_vault(service, 'sara-cv', 'key-ref-1', manifest)
        manifest.health_path = Safe_Str__Manifest__Path('tampered')          # tamper after the signature was made
        response = service.wake('sara-cv')
        assert response.outcome == Enum__Wake__Outcome.REJECTED_UNVERIFIED
        # nothing started — no instance allocated
        slug = service.slug_validator.to_slug('sara-cv')
        assert service.instances.state(slug) == Enum__Instance__State.UNKNOWN

    def test_wake_bad_manifest_rejected(self):
        service        = _service()
        bad_manifest   = Schema__Vault_App__Manifest(app_type=Enum__Vault_App__Type.STATIC_SITE,
                                                     runtime =Enum__Vault_App__Runtime.NODE)   # incompatible
        bad_manifest.content_root = Safe_Str__Manifest__Path('public')
        bad_manifest.health_path  = Safe_Str__Manifest__Path('healthz')
        _seed_vault(service, 'sara-cv', 'key-ref-1', bad_manifest)
        response = service.wake('sara-cv')
        assert response.outcome == Enum__Wake__Outcome.REJECTED_BAD_MANIFEST
