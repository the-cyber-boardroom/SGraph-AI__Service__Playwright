# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Endpoint__Resolver__EC2
# Resolves a slug to a live EC2 endpoint via the tag-backed Slug__Registry.
# Registry.get_instance() does a single ec2.describe_instances filtered on
# tag:sg:slug + tag:StackType=vault-app — no SSM round-trip.
#
# Multi-region scan: a slug's EC2 instance can live in any AWS region (the
# `sg vp register` CLI takes a --region flag), but the waker Lambda runs in
# one region. To avoid silently failing when a slug was registered in a
# different region than the waker, we scan a configurable list of regions
# (env WAKER_SCAN_REGIONS=comma-list) defaulting to the waker's own region
# + the most common ones. First hit wins, region is cached with the slug
# entry, subsequent invocations skip the scan.
#
# Module-level cache: describe_instances is ~100ms; the slug entry only
# changes on register/unpublish. 60s TTL means warm Lambda invocations skip
# the API call while still recognising unpublish within 60s.
#
# boto3 EXCEPTION — narrow usage for start_instances only (describe goes
# through the registry's boto3 boundary).
# ═══════════════════════════════════════════════════════════════════════════════

import os
import time
from typing import Optional, Callable

import boto3                                                                       # EXCEPTION — see module header

from sg_compute_specs.vault_publish.service.Slug__Registry                        import Slug__Registry
from sg_compute_specs.vault_publish.lambdas.waker.schemas.Enum__Instance__State           import Enum__Instance__State
from sg_compute_specs.vault_publish.lambdas.waker.schemas.Schema__Endpoint__Resolution    import Schema__Endpoint__Resolution
from sg_compute_specs.vault_publish.lambdas.waker.Endpoint__Resolver                      import Endpoint__Resolver

_SLUG_CACHE : dict = {}                                                            # {slug: (instance_dict, region, cached_at)}
_CACHE_TTL  = 60                                                                   # seconds


def _instance_has_tls(instance: dict) -> bool:
    for t in instance.get('Tags', []) or []:
        if t.get('Key') == 'StackTLS' and str(t.get('Value', '')).lower() in ('true', '1', 'yes'):
            return True
    return False


def _build_vault_url(public_ip: str, *, tls: bool) -> str:
    if not public_ip:
        return ''
    if tls:
        return f'https://{public_ip}/'                                                # vault-app on :443 when TLS configured
    return f'http://{public_ip}:8080'                                                  # plain HTTP fallback


def _scan_regions() -> list:
    # Caller-supplied override wins; otherwise waker's deploy region first,
    # then the most common alternatives. Deduplicated while preserving order.
    raw = os.environ.get('WAKER_SCAN_REGIONS', '')
    if raw:
        regions = [r.strip() for r in raw.split(',') if r.strip()]
    else:
        deploy_region = os.environ.get('WAKER_DEPLOY_REGION', '') \
                         or os.environ.get('AWS_REGION', '') \
                         or os.environ.get('AWS_DEFAULT_REGION', '') \
                         or 'eu-west-2'
        regions = [deploy_region, 'eu-west-2', 'us-east-1', 'us-west-2', 'eu-west-1']
    seen = set()
    return [r for r in regions if not (r in seen or seen.add(r))]


def _cached_get(registry: Slug__Registry, slug: str):
    now = time.time()
    if slug in _SLUG_CACHE:
        instance, region, ts, scan = _SLUG_CACHE[slug]
        if now - ts < _CACHE_TTL:
            return instance, region, scan
    scan = []                                                                       # list of (region, 'found'|'not_found') tuples
    found_instance = None
    found_region   = ''
    for region in _scan_regions():
        instance = registry.get_instance(slug, region=region)
        scan.append((region, 'found' if instance else 'not_found'))
        if instance is not None:
            found_instance = instance
            found_region   = region
            break
    if found_instance is not None:
        _SLUG_CACHE[slug] = (found_instance, found_region, now, scan)
    return found_instance, found_region, scan


class Endpoint__Resolver__EC2(Endpoint__Resolver):

    _registry_factory : Optional[Callable] = None                                 # Seam for in-memory testing

    def _registry(self) -> Slug__Registry:
        if self._registry_factory:
            return self._registry_factory()
        return Slug__Registry()

    def _ec2_client(self, region: str):                                            # boto3 seam — subclass overrides for testing
        return boto3.client('ec2', region_name=region)

    def resolve(self, slug: str) -> Schema__Endpoint__Resolution:
        registry                    = self._registry()
        instance, region, scan      = _cached_get(registry, slug)
        scan_summary                = ', '.join(f'{r}={result}' for r, result in scan)
        if not instance:
            return Schema__Endpoint__Resolution(
                slug             = slug,
                state            = Enum__Instance__State.UNKNOWN,
                regions_scanned  = scan_summary,
            )
        iid       = instance.get('InstanceId', '')
        raw_state = instance.get('State', {}).get('Name', 'unknown')
        public_ip = instance.get('PublicIpAddress', '')
        # Detect StackTLS tag — vault-app on HTTPS:443 when TLS is configured,
        # plain HTTP:8080 when not. The HTTPS URL points at the IP, so the
        # proxy must skip cert validation (Endpoint__Proxy__HTTP handles
        # that — the upstream cert is for the FQDN, not the IP).
        tls       = _instance_has_tls(instance)
        vault_url = _build_vault_url(public_ip, tls=tls)
        return Schema__Endpoint__Resolution(
            slug            = slug,
            instance_id     = iid,
            public_ip       = public_ip,
            vault_url       = vault_url,
            state           = self._parse_state(raw_state),
            region          = region,
            regions_scanned = scan_summary,
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
        for instance, region, _ts, _scan in _SLUG_CACHE.values():
            if instance.get('InstanceId', '') == instance_id and region:
                return region
        return self._registry().region or 'eu-west-2'

    def _parse_state(self, raw: str) -> Enum__Instance__State:
        try:
            return Enum__Instance__State(raw)
        except ValueError:
            return Enum__Instance__State.UNKNOWN
