# ═══════════════════════════════════════════════════════════════════════════════
# vault-publish — Publish__Service
# The orchestrator. One service layer behind the CLI, the FastAPI routes and the
# waker Lambda — every caller constructs a request and calls one of these
# methods. Composes Slug__Validator, Slug__Resolver, Vault__Fetcher,
# Manifest__Verifier, Manifest__Interpreter, Instance__Manager and
# Control_Plane__Client.
#
# Inject the *__In_Memory variants of the SG/Send-boundary classes
# (Slug__Resolver, Vault__Fetcher, Manifest__Verifier) for tests and local
# composition — the base classes raise NotImplementedError until the SG/Send
# contracts (open questions #1, #3, #4 in the dev pack) are confirmed.
#
# _billing stands in for the SG/Send billing-record store: in production the
# billing record is read from SG/Send, not held here. It is the only per-slug
# state and the integrity anchor.
# ═══════════════════════════════════════════════════════════════════════════════

from datetime                                                import datetime, timezone

from osbot_utils.type_safe.Type_Safe                         import Type_Safe

from vault_publish.schemas.Enum__Instance__State             import Enum__Instance__State
from vault_publish.schemas.Enum__Publish__Error_Code         import Enum__Publish__Error_Code
from vault_publish.schemas.Enum__Wake__Outcome               import Enum__Wake__Outcome
from vault_publish.schemas.Safe_Str__Instance__Id            import Safe_Str__Instance__Id
from vault_publish.schemas.Safe_Str__Message                 import Safe_Str__Message
from vault_publish.schemas.Safe_Str__Owner_Id                import Safe_Str__Owner_Id
from vault_publish.schemas.Safe_Str__Signing_Key_Ref         import Safe_Str__Signing_Key_Ref
from vault_publish.schemas.Safe_Str__Slug                    import Safe_Str__Slug
from vault_publish.schemas.List__Slug                        import List__Slug
from vault_publish.schemas.Schema__Slug__Billing_Record      import Schema__Slug__Billing_Record
from vault_publish.schemas.Schema__VaultPublish__Health__Response    import Schema__VaultPublish__Health__Response
from vault_publish.schemas.Schema__VaultPublish__List__Response      import Schema__VaultPublish__List__Response
from vault_publish.schemas.Schema__VaultPublish__Register__Response  import Schema__VaultPublish__Register__Response
from vault_publish.schemas.Schema__VaultPublish__Resolve__Response   import Schema__VaultPublish__Resolve__Response
from vault_publish.schemas.Schema__VaultPublish__Status__Response    import Schema__VaultPublish__Status__Response
from vault_publish.schemas.Schema__VaultPublish__Unpublish__Response import Schema__VaultPublish__Unpublish__Response
from vault_publish.schemas.Schema__VaultPublish__Wake__Response      import Schema__VaultPublish__Wake__Response
from vault_publish.service.Control_Plane__Client             import Control_Plane__Client
from vault_publish.service.Instance__Manager                 import Instance__Manager
from vault_publish.service.Manifest__Interpreter             import Manifest__Interpreter
from vault_publish.service.Manifest__Verifier                import Manifest__Verifier
from vault_publish.service.Slug__Resolver                    import Slug__Resolver
from vault_publish.service.Slug__Validator                   import Slug__Validator
from vault_publish.service.Vault__Fetcher                    import Vault__Fetcher

SGRAPH_APP_DOMAIN = 'sgraph.app'


class Publish__Service(Type_Safe):
    slug_validator    : Slug__Validator
    slug_resolver     : Slug__Resolver                                       # inject *__In_Memory for tests / local
    vault_fetcher     : Vault__Fetcher                                       # inject *__In_Memory for tests / local
    manifest_verifier : Manifest__Verifier                                   # inject *__In_Memory for tests / local
    interpreter       : Manifest__Interpreter
    instances         : Instance__Manager
    control_plane     : Control_Plane__Client
    _billing          : dict                                                 # slug(str) → Schema__Slug__Billing_Record

    # ── helpers ──────────────────────────────────────────────────────────────

    def url_for(self, slug) -> str:
        return f'https://{slug}.{SGRAPH_APP_DOMAIN}/'

    def _now(self) -> str:
        return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # ── register ─────────────────────────────────────────────────────────────

    def register(self, raw_slug: str, owner_id: str,
                 signing_public_key_ref: str) -> tuple:                       # -> (response|None, error_code|None)
        slug_error = self.slug_validator.validate(raw_slug)
        if slug_error is not None:
            return None, slug_error
        slug = self.slug_validator.to_slug(raw_slug)
        if str(slug) in self._billing:
            return None, Enum__Publish__Error_Code.SLUG_TAKEN
        now    = self._now()
        record = Schema__Slug__Billing_Record(
            slug                   = slug                                      ,
            owner_id               = Safe_Str__Owner_Id       (str(owner_id))   ,
            signing_public_key_ref = Safe_Str__Signing_Key_Ref(str(signing_public_key_ref)),
            created_at             = Safe_Str__Message        (now)             ,
            updated_at             = Safe_Str__Message        (now)             ,
        )
        self._billing[str(slug)] = record
        response = Schema__VaultPublish__Register__Response(
            slug       = slug                                  ,
            owner_id   = record.owner_id                       ,
            url        = Safe_Str__Message(self.url_for(slug))  ,
            registered = True                                  ,
        )
        return response, None

    # ── unpublish ────────────────────────────────────────────────────────────

    def unpublish(self, raw_slug: str) -> tuple:                              # -> (response|None, error_code|None)
        slug_error = self.slug_validator.validate(raw_slug)
        if slug_error is not None:
            return None, slug_error
        slug    = self.slug_validator.to_slug(raw_slug)
        existed = str(slug) in self._billing
        self._billing.pop(str(slug), None)
        if existed:
            self.instances.stop(slug)                                         # association gone → instance stops
        response = Schema__VaultPublish__Unpublish__Response(slug        = slug    ,
                                                             unpublished = existed )
        return response, None

    # ── status ───────────────────────────────────────────────────────────────

    def status(self, raw_slug: str) -> tuple:                                 # -> (response|None, error_code|None)
        slug_error = self.slug_validator.validate(raw_slug)
        if slug_error is not None:
            return None, slug_error
        slug   = self.slug_validator.to_slug(raw_slug)
        record = self.instances.record(slug)
        response = Schema__VaultPublish__Status__Response(
            slug           = slug                                ,
            registered     = str(slug) in self._billing          ,
            instance_state = record.state                        ,
            instance_id    = record.instance_id                  ,
            url            = Safe_Str__Message(self.url_for(slug)),
        )
        return response, None

    # ── list ─────────────────────────────────────────────────────────────────

    def list(self) -> Schema__VaultPublish__List__Response:
        slugs = List__Slug()
        for key in sorted(self._billing.keys()):
            slugs.append(Safe_Str__Slug(key))
        return Schema__VaultPublish__List__Response(slugs=slugs)

    # ── resolve (no side effects) ────────────────────────────────────────────

    def resolve(self, raw_slug: str) -> tuple:                                # -> (response|None, error_code|None)
        slug_error = self.slug_validator.validate(raw_slug)
        if slug_error is not None:
            return None, slug_error
        slug                = self.slug_validator.to_slug(raw_slug)
        folder_ref          = self.slug_resolver.resolve(slug)
        manifest, signature = self.vault_fetcher.fetch(folder_ref)
        if manifest is None:
            return None, Enum__Publish__Error_Code.VAULT_NOT_FOUND
        response = Schema__VaultPublish__Resolve__Response(
            slug        = slug                    ,
            transfer_id = folder_ref.transfer_id  ,
            read_key    = folder_ref.read_key     ,
            app_type    = manifest.app_type       ,
            runtime     = manifest.runtime        ,
        )
        return response, None

    # ── wake (the route the waker Lambda calls) ──────────────────────────────

    def wake(self, raw_slug: str) -> Schema__VaultPublish__Wake__Response:
        # wake always returns a Wake response — the outcome enum carries any
        # rejection reason, so the waker can always decide warming-page vs proxy.
        slug_error = self.slug_validator.validate(raw_slug)
        if slug_error is not None:
            return self._wake_rejected(Safe_Str__Slug()                                  ,
                                       Enum__Wake__Outcome.REJECTED_INVALID_SLUG          ,
                                       Enum__Instance__State.UNKNOWN                      ,
                                       self.slug_validator.message_for(slug_error)        )
        slug    = self.slug_validator.to_slug(raw_slug)
        billing = self._billing.get(str(slug))
        if billing is None:
            return self._wake_rejected(slug                                              ,
                                       Enum__Wake__Outcome.REJECTED_NOT_REGISTERED        ,
                                       self.instances.state(slug)                         ,
                                       'slug is not registered'                           )

        folder_ref          = self.slug_resolver.resolve(slug)
        manifest, signature = self.vault_fetcher.fetch(folder_ref)
        if manifest is None:
            return self._wake_rejected(slug                                              ,
                                       Enum__Wake__Outcome.REJECTED_VAULT_NOT_FOUND       ,
                                       self.instances.state(slug)                         ,
                                       'no vault folder at the slug\'s derived location'  )

        if not self.manifest_verifier.verify(manifest, signature, billing):
            return self._wake_rejected(slug                                              ,
                                       Enum__Wake__Outcome.REJECTED_UNVERIFIED            ,
                                       self.instances.state(slug)                         ,
                                       'manifest signature failed verification — nothing started')

        plan, manifest_error = self.interpreter.interpret(manifest)
        if manifest_error is not None:
            return self._wake_rejected(slug                                              ,
                                       Enum__Wake__Outcome.REJECTED_BAD_MANIFEST          ,
                                       self.instances.state(slug)                         ,
                                       f'manifest could not be interpreted: {manifest_error.value}')

        record, was_running = self.instances.start(slug)
        control_plane_key   = self.control_plane.generate_key()
        self.control_plane.provision(slug, record.instance_id, control_plane_key, plan)

        outcome = Enum__Wake__Outcome.ALREADY_RUNNING if was_running else Enum__Wake__Outcome.STARTED
        detail  = ('instance already running' if was_running
                   else 'instance starting — serve the warming page')
        return Schema__VaultPublish__Wake__Response(
            slug           = slug                       ,
            outcome        = outcome                    ,
            instance_state = record.state               ,
            instance_id    = record.instance_id         ,
            warming        = not was_running            ,
            detail         = Safe_Str__Message(detail)  ,
        )

    def _wake_rejected(self, slug, outcome, instance_state, detail) -> Schema__VaultPublish__Wake__Response:
        return Schema__VaultPublish__Wake__Response(
            slug           = slug                          ,
            outcome        = outcome                       ,
            instance_state = instance_state                ,
            instance_id    = Safe_Str__Instance__Id()      ,
            warming        = False                         ,
            detail         = Safe_Str__Message(detail)     ,
        )

    # ── health ───────────────────────────────────────────────────────────────

    def health(self) -> Schema__VaultPublish__Health__Response:
        # The four infrastructure layers (DNS, ACM cert, CloudFront distribution,
        # waker Lambda) are provisioned by DevOps and verified against live AWS —
        # see dev pack 09__dev-ops. The Python-package build cannot reach AWS, so
        # it reports the layers as unverified rather than guessing.
        return Schema__VaultPublish__Health__Response(
            dns_ok          = False ,
            cert_ok         = False ,
            distribution_ok = False ,
            waker_ok        = False ,
            detail          = Safe_Str__Message('infrastructure-layer checks are not wired '
                                                'in the Python-package build — see dev pack 09__dev-ops'),
        )
