# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Endpoint__Resolver__EC2
# Resolves a slug to a live EC2 endpoint via the tag-backed Slug__Registry.
# Registry.get_instance() does a single ec2.describe_instances filtered on
# tag:sg:slug + tag:StackType=vault-app — no SSM round-trip.
#
# Module-level cache: SSM is gone but describe_instances is still ~100ms and
# the registry entry only changes on register/unpublish. 60s TTL means warm
# Lambda invocations skip the API call while still recognising unpublish
# within 60s.
#
# boto3 EXCEPTION — narrow usage for start_instances only (describe goes
# through the registry's boto3 boundary).
# ═══════════════════════════════════════════════════════════════════════════════

import time
from typing import Optional, Callable

import boto3                                                                       # EXCEPTION — see module header

from sg_compute_specs.vault_publish.service.Slug__Registry                        import Slug__Registry
from sg_compute_specs.vault_publish.waker.schemas.Enum__Instance__State           import Enum__Instance__State
from sg_compute_specs.vault_publish.waker.schemas.Schema__Endpoint__Resolution    import Schema__Endpoint__Resolution
from sg_compute_specs.vault_publish.waker.Endpoint__Resolver                      import Endpoint__Resolver

_SLUG_CACHE : dict = {}                                                            # {slug: (instance_dict, region, cached_at)}
_CACHE_TTL  = 60                                                                   # seconds


def _cached_get(registry: Slug__Registry, slug: str):
    now = time.time()
    if slug in _SLUG_CACHE:
        instance, region, ts = _SLUG_CACHE[slug]
        if now - ts < _CACHE_TTL:
            return instance, region
    instance = registry.get_instance(slug)
    region   = registry.region or ''
    if instance is not None:
        _SLUG_CACHE[slug] = (instance, region, now)
    return instance, region


class Endpoint__Resolver__EC2(Endpoint__Resolver):

    _registry_factory : Optional[Callable] = None                                 # Seam for in-memory testing

    def _registry(self) -> Slug__Registry:
        if self._registry_factory:
            return self._registry_factory()
        return Slug__Registry()

    def _ec2_client(self, region: str):                                            # boto3 seam — subclass overrides for testing
        return boto3.client('ec2', region_name=region)

    def resolve(self, slug: str) -> Schema__Endpoint__Resolution:
        registry          = self._registry()
        instance, region  = _cached_get(registry, slug)
        if not instance:
            return Schema__Endpoint__Resolution(slug=slug, state=Enum__Instance__State.UNKNOWN)
        region    = region or (registry.region or '')
        iid       = instance.get('InstanceId', '')
        raw_state = instance.get('State', {}).get('Name', 'unknown')
        public_ip = instance.get('PublicIpAddress', '')
        vault_url = f'http://{public_ip}:8080' if public_ip else ''
        return Schema__Endpoint__Resolution(
            slug        = slug,
            instance_id = iid,
            public_ip   = public_ip,
            vault_url   = vault_url,
            state       = self._parse_state(raw_state),
            region      = region,
        )

    def start(self, instance_id: str) -> bool:
        # The cached entry tells us the region; fall back to the registry's
        # default region if we lost the cache (rare).
        region = self._region_for(instance_id)
        try:
            self._ec2_client(region).start_instances(InstanceIds=[instance_id])
            return True
        except Exception:
            return False

    def _region_for(self, instance_id: str) -> str:
        for instance, region, _ts in _SLUG_CACHE.values():
            if instance.get('InstanceId', '') == instance_id and region:
                return region
        return self._registry().region or 'eu-west-2'

    def _parse_state(self, raw: str) -> Enum__Instance__State:
        try:
            return Enum__Instance__State(raw)
        except ValueError:
            return Enum__Instance__State.UNKNOWN
