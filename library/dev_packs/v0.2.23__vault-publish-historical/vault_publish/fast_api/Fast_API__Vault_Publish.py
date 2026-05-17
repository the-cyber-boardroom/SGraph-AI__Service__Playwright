# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Fast_API__Vault_Publish
# Local / dev composer for the vault-publish FastAPI app. Importable without
# side effects; one Publish__Service instance is shared across all requests, so
# state (registered slugs, instance lifecycle) persists for the life of the
# process — which is what makes it usable for interactive testing.
#
# The three SG/Send-boundary classes are wired with their deterministic
# *__In_Memory stand-ins (the base classes raise NotImplementedError until the
# SG/Send contracts are confirmed — see dev pack open questions #1, #3, #4).
#
# setup() also seeds one demo slug end to end ('hello-world') with a correctly
# signed static-site manifest, because the manifest-publish step is on the
# SG/Send side and has no endpoint here — without the seed, wake() on a freshly
# registered slug would always return rejected-vault-not-found.
#
# This composer uses the plain Fast_API base (no API key) for open dev mode.
# Production wiring (Serverless__Fast_API + auth) is a later, separate step.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_fast_api.api.Fast_API                             import Fast_API

from vault_publish.fast_api.Routes__Vault_Publish            import Routes__Vault_Publish
from vault_publish.schemas.Enum__Vault_App__Runtime          import Enum__Vault_App__Runtime
from vault_publish.schemas.Enum__Vault_App__Type             import Enum__Vault_App__Type
from vault_publish.schemas.Safe_Str__Manifest__Path          import Safe_Str__Manifest__Path
from vault_publish.schemas.Schema__Vault_App__Manifest       import Schema__Vault_App__Manifest
from vault_publish.service.Manifest__Verifier__In_Memory     import Manifest__Verifier__In_Memory
from vault_publish.service.Publish__Service                  import Publish__Service
from vault_publish.service.Slug__Resolver__In_Memory         import Slug__Resolver__In_Memory
from vault_publish.service.Vault__Fetcher__In_Memory         import Vault__Fetcher__In_Memory

DEMO_SLUG    = 'hello-world'
DEMO_KEY_REF = 'demo-signing-key'


def build_service() -> Publish__Service:
    return Publish__Service(slug_resolver     = Slug__Resolver__In_Memory()    ,
                            vault_fetcher     = Vault__Fetcher__In_Memory()    ,
                            manifest_verifier = Manifest__Verifier__In_Memory())


def seed_demo_slug(service: Publish__Service) -> None:
    service.register(DEMO_SLUG, 'demo-owner', DEMO_KEY_REF)
    manifest   = Schema__Vault_App__Manifest(app_type     = Enum__Vault_App__Type.STATIC_SITE  ,
                                             runtime      = Enum__Vault_App__Runtime.STATIC    ,
                                             content_root = Safe_Str__Manifest__Path('public') ,
                                             health_path  = Safe_Str__Manifest__Path('healthz'))
    slug       = service.slug_validator.to_slug(DEMO_SLUG)
    folder_ref = service.slug_resolver.resolve(slug)
    signature  = service.manifest_verifier.sign(manifest, DEMO_KEY_REF)
    service.vault_fetcher.publish(folder_ref, manifest, signature)


class Fast_API__Vault_Publish(Fast_API):

    def setup(self) -> 'Fast_API__Vault_Publish':
        super().setup()
        service = build_service()
        seed_demo_slug(service)
        self.add_routes(Routes__Vault_Publish, service=service)
        return self
