# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Waker__Lambda__Adapter (no mocks, no patches)
# Host-header parsing and the wake handoff — the pure, testable core of the edge.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from vault_publish.schemas.Enum__Vault_App__Runtime      import Enum__Vault_App__Runtime
from vault_publish.schemas.Enum__Vault_App__Type         import Enum__Vault_App__Type
from vault_publish.schemas.Enum__Wake__Outcome           import Enum__Wake__Outcome
from vault_publish.schemas.Safe_Str__Manifest__Path      import Safe_Str__Manifest__Path
from vault_publish.schemas.Schema__Vault_App__Manifest   import Schema__Vault_App__Manifest
from vault_publish.service.Manifest__Verifier__In_Memory import Manifest__Verifier__In_Memory
from vault_publish.service.Publish__Service              import Publish__Service
from vault_publish.service.Slug__Resolver__In_Memory     import Slug__Resolver__In_Memory
from vault_publish.service.Vault__Fetcher__In_Memory     import Vault__Fetcher__In_Memory
from vault_publish.waker.Waker__Lambda__Adapter          import Waker__Lambda__Adapter


def _service() -> Publish__Service:
    return Publish__Service(slug_resolver     = Slug__Resolver__In_Memory()    ,
                            vault_fetcher     = Vault__Fetcher__In_Memory()    ,
                            manifest_verifier = Manifest__Verifier__In_Memory())


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


class test_Waker__Lambda__Adapter(TestCase):

    def setUp(self):
        self.adapter = Waker__Lambda__Adapter(service=_service())

    # ── slug_from_host ───────────────────────────────────────────────────────

    def test_slug_from_apex_wildcard(self):
        assert self.adapter.slug_from_host('sara-cv.sgraph.app') == 'sara-cv'

    def test_slug_from_env_wildcard(self):
        assert self.adapter.slug_from_host('sara-cv.qa.sgraph.app')   == 'sara-cv'
        assert self.adapter.slug_from_host('sara-cv.dev.sgraph.app')  == 'sara-cv'

    def test_slug_from_host_strips_port(self):
        assert self.adapter.slug_from_host('sara-cv.sgraph.app:443') == 'sara-cv'

    def test_bare_apex_has_no_slug(self):
        assert self.adapter.slug_from_host('sgraph.app') == ''

    def test_unrelated_host_has_no_slug(self):
        assert self.adapter.slug_from_host('example.com') == ''

    # ── handle ───────────────────────────────────────────────────────────────

    def test_handle_cold_slug_returns_started(self):
        _seed_vault(self.adapter.service, 'sara-cv', 'key-ref-1')
        response = self.adapter.handle('sara-cv.sgraph.app')
        assert response.outcome == Enum__Wake__Outcome.STARTED
        assert response.warming is True

    def test_handle_unknown_host_rejected(self):
        response = self.adapter.handle('sgraph.app')
        assert response.outcome == Enum__Wake__Outcome.REJECTED_INVALID_SLUG

    # ── warming_page_html ────────────────────────────────────────────────────

    def test_warming_page_contains_slug_and_refresh(self):
        _seed_vault(self.adapter.service, 'sara-cv', 'key-ref-1')
        response = self.adapter.handle('sara-cv.sgraph.app')
        html     = self.adapter.warming_page_html(response)
        assert 'sara-cv'        in html
        assert 'http-equiv'     in html
        assert 'refresh'        in html
