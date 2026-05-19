# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Slug__Registry
# EC2-tag-backed registry of published slugs. The vault-app EC2 instance is
# the single source of truth — three tags carry the routing metadata:
#
#   sg:slug   — the slug name (key the waker filters on)
#   sg:fqdn   — fully-qualified hostname (e.g. sara-cv.aws.sg-labs.app)
#   sg:zone   — DNS apex (e.g. aws.sg-labs.app)
#
# These augment the existing StackName / StackType=vault-app tags written by
# Vault_App__Service.create_stack(). The slug is durable for the lifetime of
# the EC2 instance — terminate the instance and the registry entry is gone.
#
# Why tags, not SSM:
#   1. Single source of truth — no risk of SSM and EC2 drifting.
#   2. Lifecycle coupling — no stale entries when an instance is terminated.
#   3. Waker IAM is simpler — only ec2:DescribeInstances + ec2:StartInstances
#      (no ssm:GetParameter grant needed).
#   4. One API call per resolve (was: SSM GetParameter + EC2 DescribeInstances).
#
# boto3 EXCEPTION — single boundary; tests inject _ec2_factory.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from datetime import datetime, timezone
from typing   import Callable, List, Optional

import boto3                                                                          # EXCEPTION — single boto3 boundary for ec2.create_tags + describe_instances
from botocore.exceptions import ClientError

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.schemas.Safe_Str__Slug              import Safe_Str__Slug
from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Entry import Schema__Vault_Publish__Entry

TAG_SLUG   = 'sg:slug'
TAG_FQDN   = 'sg:fqdn'
TAG_ZONE   = 'sg:zone'
TAG_STYPE  = 'StackType'
STYPE_VAL  = 'vault-app'


DEFAULT_REGION = os.environ.get('AWS_DEFAULT_REGION', 'eu-west-2')


class Slug__Registry(Type_Safe):
    _ec2_factory : Optional[Callable] = None                                          # seam: (region: str) -> ec2 client; tests inject in-memory fake

    region : str = ''                                                                  # default region for get/list_all when caller doesn't specify

    def _ec2(self, region: str = ''):
        r = region or self.region or DEFAULT_REGION
        if self._ec2_factory is not None:
            return self._ec2_factory(r)
        return boto3.client('ec2', region_name=r)

    # ── writes ───────────────────────────────────────────────────────────────

    def put(self, slug: str, fqdn: str, region: str, instance_id: str) -> bool:
        # Tag an existing vault-app EC2 instance with the routing metadata.
        # Caller must have already provisioned the instance via Vault_App__Service.
        zone = fqdn.split('.', 1)[1] if '.' in fqdn else ''
        try:
            self._ec2(region).create_tags(
                Resources=[instance_id],
                Tags=[
                    {'Key': TAG_SLUG, 'Value': slug},
                    {'Key': TAG_FQDN, 'Value': fqdn},
                    {'Key': TAG_ZONE, 'Value': zone},
                ],
            )
            return True
        except ClientError:
            return False

    def delete(self, slug: str, region: str = '') -> bool:
        # No-op for the SSM-era contract: the EC2 instance termination removes
        # all tags. Returns True iff a matching instance existed *before* the
        # caller-driven termination, so the unpublish flow can confirm action.
        return self.get(slug, region) is not None

    # ── reads ────────────────────────────────────────────────────────────────

    def get(self, slug: str, region: str = '') -> Optional[Schema__Vault_Publish__Entry]:
        instance = self._find_instance(slug, region)
        if instance is None:
            return None
        return self._to_entry(slug, instance, region or self.region or DEFAULT_REGION)

    def get_instance(self, slug: str, region: str = '') -> Optional[dict]:
        # Raw boto3 instance dict — used by Endpoint__Resolver__EC2 to avoid
        # a second describe_instances call after the registry lookup.
        return self._find_instance(slug, region)

    def list_all(self, region: str = '') -> List[str]:
        ec2 = self._ec2(region)
        try:
            resp = ec2.describe_instances(Filters=[
                {'Name': 'tag-key',                 'Values': [TAG_SLUG]},
                {'Name': f'tag:{TAG_STYPE}',        'Values': [STYPE_VAL]},
                {'Name': 'instance-state-name',     'Values': ['running', 'stopped', 'pending', 'stopping']},
            ])
        except ClientError:
            return []
        slugs = []
        for reservation in resp.get('Reservations', []):
            for inst in reservation.get('Instances', []):
                slug = _tag(inst, TAG_SLUG)
                if slug:
                    slugs.append(slug)
        return slugs

    # ── internal ─────────────────────────────────────────────────────────────

    def _find_instance(self, slug: str, region: str = '') -> Optional[dict]:
        # Primary lookup: tag:sg:slug — set by `sg vp register` / `sg vp adopt`.
        # Fallback   : tag:StackName — covers instances created via `sg va create`
        # directly (without going through the vault-publish flow). The fallback
        # makes the system more forgiving but the operator should still run
        # `sg vp adopt <slug>` (or the tag-slug RPC) to add the explicit
        # sg:slug tag for consistency with the rest of the toolchain.
        ec2 = self._ec2(region)
        for tag_key in (TAG_SLUG, 'StackName'):
            try:
                resp = ec2.describe_instances(Filters=[
                    {'Name': f'tag:{tag_key}',          'Values': [slug]},
                    {'Name': f'tag:{TAG_STYPE}',        'Values': [STYPE_VAL]},
                    {'Name': 'instance-state-name',     'Values': ['running', 'stopped', 'pending', 'stopping']},
                ])
            except ClientError:
                continue
            for reservation in resp.get('Reservations', []):
                instances = reservation.get('Instances', [])
                if instances:
                    return instances[0]
        return None

    def _to_entry(self, slug: str, instance: dict, region: str) -> Schema__Vault_Publish__Entry:
        fqdn       = _tag(instance, TAG_FQDN)
        stack_name = _tag(instance, 'StackName') or slug
        launch     = instance.get('LaunchTime')
        created_at = launch.strftime('%Y-%m-%dT%H:%M:%SZ') if hasattr(launch, 'strftime') else str(launch or '')
        return Schema__Vault_Publish__Entry(
            slug       = Safe_Str__Slug(slug),
            stack_name = stack_name,
            fqdn       = fqdn,
            region     = region,
            created_at = created_at,
        )


def _tag(instance: dict, key: str) -> str:
    for t in instance.get('Tags', []) or []:
        if t.get('Key') == key:
            return t.get('Value', '')
    return ''
