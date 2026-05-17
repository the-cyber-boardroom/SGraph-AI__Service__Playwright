# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Vault_Publish__Service
# Orchestrator: register / unpublish / status / list.
# bootstrap() is a Phase 2d stub that exits non-zero until landed.
#
# Dependencies injected via Optional factory seams so unit tests compose
# in-memory fakes without touching AWS. Flat scheme: <slug>.aws.sg-labs.app
# (decided 2026-05-17, Q3 — no namespace field in requests or responses).
# ═══════════════════════════════════════════════════════════════════════════════

import os
import time
from datetime import datetime, timezone
from typing   import Callable, Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.schemas.Enum__Slug__Error_Code              import Enum__Slug__Error_Code
from sg_compute_specs.vault_publish.schemas.Enum__Vault_Publish__State          import Enum__Vault_Publish__State
from sg_compute_specs.vault_publish.schemas.Safe_Str__Slug                      import Safe_Str__Slug
from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Entry        import Schema__Vault_Publish__Entry
from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__List__Response   import Schema__Vault_Publish__List__Response
from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Register__Request  import Schema__Vault_Publish__Register__Request
from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Register__Response import Schema__Vault_Publish__Register__Response
from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Status__Response   import Schema__Vault_Publish__Status__Response
from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Unpublish__Response import Schema__Vault_Publish__Unpublish__Response
from sg_compute_specs.vault_publish.service.Slug__Registry  import Slug__Registry
from sg_compute_specs.vault_publish.service.Slug__Validator import Slug__Validator

DEFAULT_ZONE_FALLBACK = 'aws.sg-labs.app'
DEFAULT_REGION        = os.environ.get('AWS_DEFAULT_REGION', 'eu-west-2')


def _default_zone() -> str:
    return os.environ.get('SG_AWS__DNS__DEFAULT_ZONE', DEFAULT_ZONE_FALLBACK)


class Vault_Publish__Service(Type_Safe):
    _registry_factory   : Optional[Callable] = None  # seam: () -> Slug__Registry
    _vault_app_factory  : Optional[Callable] = None  # seam: () -> Vault_App__Service
    _validator          : Optional[Slug__Validator] = None

    def setup(self) -> 'Vault_Publish__Service':
        self._validator = Slug__Validator()
        return self

    def _registry(self) -> Slug__Registry:
        if self._registry_factory is not None:
            return self._registry_factory()
        return Slug__Registry()

    def _vault_app(self):
        if self._vault_app_factory is not None:
            return self._vault_app_factory()
        from sg_compute_specs.vault_app.service.Vault_App__Service import Vault_App__Service
        return Vault_App__Service().setup()

    def _validator_or_default(self) -> Slug__Validator:
        return self._validator or Slug__Validator()

    def register(self, request: Schema__Vault_Publish__Register__Request) -> Schema__Vault_Publish__Register__Response:
        t0      = time.monotonic()
        slug    = str(request.slug).strip()
        region  = str(request.region) or DEFAULT_REGION
        err     = self._validator_or_default().validate(slug)
        if err is not None:
            return Schema__Vault_Publish__Register__Response(
                slug      = request.slug,
                message   = f'invalid slug: {err}',
                elapsed_ms = int((time.monotonic() - t0) * 1000))

        registry = self._registry()
        if registry.get(slug) is not None:
            return Schema__Vault_Publish__Register__Response(
                slug      = request.slug,
                message   = f'slug already registered: {slug}',
                elapsed_ms = int((time.monotonic() - t0) * 1000))

        fqdn       = f'{slug}.{_default_zone()}'
        vault_app  = self._vault_app()
        from sg_compute_specs.vault_app.schemas.Schema__Vault_App__Create__Request import Schema__Vault_App__Create__Request
        create_req           = Schema__Vault_App__Create__Request()
        create_req.stack_name  = slug
        create_req.region      = region
        create_req.with_aws_dns = True
        create_req.tls_hostname = fqdn
        create_req.tls_mode     = 'letsencrypt-hostname'
        create_resp = vault_app.create_stack(create_req)

        stack_name = str(getattr(create_resp.stack_info, 'stack_name', '') or slug)
        registry.put(slug       = slug,
                     vault_key  = str(request.vault_key),
                     stack_name = stack_name,
                     fqdn       = fqdn,
                     region     = region)
        return Schema__Vault_Publish__Register__Response(
            slug       = request.slug,
            fqdn       = fqdn,
            stack_name = stack_name,
            message    = 'registered',
            elapsed_ms = int((time.monotonic() - t0) * 1000))

    def unpublish(self, slug: str) -> Schema__Vault_Publish__Unpublish__Response:
        t0       = time.monotonic()
        registry = self._registry()
        entry    = registry.get(slug)
        if entry is None:
            return Schema__Vault_Publish__Unpublish__Response(
                slug      = Safe_Str__Slug(slug),
                message   = f'slug not found: {slug}',
                elapsed_ms = int((time.monotonic() - t0) * 1000))

        stack_name = str(entry.stack_name)
        region     = str(entry.region) or DEFAULT_REGION
        vault_app  = self._vault_app()
        vault_app.delete_stack(region, stack_name)
        registry.delete(slug)
        return Schema__Vault_Publish__Unpublish__Response(
            slug       = Safe_Str__Slug(slug),
            deleted    = True,
            stack_name = stack_name,
            message    = 'unpublished',
            elapsed_ms = int((time.monotonic() - t0) * 1000))

    def status(self, slug: str) -> Schema__Vault_Publish__Status__Response:
        t0       = time.monotonic()
        registry = self._registry()
        entry    = registry.get(slug)
        if entry is None:
            return Schema__Vault_Publish__Status__Response(
                slug      = Safe_Str__Slug(slug),
                state     = Enum__Vault_Publish__State.UNKNOWN,
                elapsed_ms = int((time.monotonic() - t0) * 1000))

        stack_name = str(entry.stack_name)
        region     = str(entry.region) or DEFAULT_REGION
        vault_app  = self._vault_app()
        info       = vault_app.get_stack_info(region, stack_name)
        if info is None:
            ec2_state = Enum__Vault_Publish__State.UNKNOWN
            public_ip = ''
            vault_url = ''
        else:
            state_raw = str(getattr(info, 'state', '') or '')
            ec2_state = _map_state(state_raw)
            public_ip = str(getattr(info, 'public_ip', '') or '')
            vault_url = str(getattr(info, 'vault_url', '') or '')
        return Schema__Vault_Publish__Status__Response(
            slug       = Safe_Str__Slug(slug),
            state      = ec2_state,
            fqdn       = str(entry.fqdn),
            vault_url  = vault_url,
            public_ip  = public_ip,
            stack_name = stack_name,
            elapsed_ms = int((time.monotonic() - t0) * 1000))

    def list_slugs(self) -> Schema__Vault_Publish__List__Response:
        t0       = time.monotonic()
        registry = self._registry()
        slugs    = registry.list_all()
        from sg_compute_specs.vault_publish.schemas.List__Schema__Vault_Publish__Entry import List__Schema__Vault_Publish__Entry
        entries  = List__Schema__Vault_Publish__Entry()
        for slug in slugs:
            entry = registry.get(slug)
            if entry is None:
                continue
            redacted = Schema__Vault_Publish__Entry(
                slug       = entry.slug,
                vault_key  = None,  # redacted in list output
                stack_name = entry.stack_name,
                fqdn       = entry.fqdn,
                region     = entry.region,
                created_at = entry.created_at)
            entries.append(redacted)
        return Schema__Vault_Publish__List__Response(
            entries    = entries,
            total      = len(entries),
            elapsed_ms = int((time.monotonic() - t0) * 1000))


def _map_state(state_raw: str) -> Enum__Vault_Publish__State:
    mapping = {
        'running' : Enum__Vault_Publish__State.RUNNING,
        'stopped' : Enum__Vault_Publish__State.STOPPED,
        'pending' : Enum__Vault_Publish__State.PENDING,
        'stopping': Enum__Vault_Publish__State.STOPPING,
    }
    return mapping.get(state_raw, Enum__Vault_Publish__State.UNKNOWN)
