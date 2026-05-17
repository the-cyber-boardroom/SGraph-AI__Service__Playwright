# ═══════════════════════════════════════════════════════════════════════════════
# Waker — Endpoint__Resolver__EC2
# Resolves a slug to a live EC2 endpoint by looking up the slug registry and
# then querying EC2 by the StackName tag.
#
# boto3 EXCEPTION — narrow usage for describe_instances + start_instances only.
# All other EC2 work goes through sg_compute platform helpers.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Optional, Callable

import boto3                                                                       # EXCEPTION — see module header

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.service.Slug__Registry                        import Slug__Registry
from sg_compute_specs.vault_publish.waker.schemas.Enum__Instance__State           import Enum__Instance__State
from sg_compute_specs.vault_publish.waker.schemas.Schema__Endpoint__Resolution    import Schema__Endpoint__Resolution
from sg_compute_specs.vault_publish.waker.Endpoint__Resolver                      import Endpoint__Resolver


class Endpoint__Resolver__EC2(Endpoint__Resolver):

    _registry_factory : Optional[Callable] = None                                 # Seam for in-memory testing

    def _registry(self) -> Slug__Registry:
        if self._registry_factory:
            return self._registry_factory()
        return Slug__Registry()

    def _ec2_client(self, region: str):                                            # boto3 seam — subclass overrides for testing
        return boto3.client('ec2', region_name=region)

    def resolve(self, slug: str) -> Schema__Endpoint__Resolution:
        entry = self._registry().get(slug)
        if not entry:
            return Schema__Endpoint__Resolution(slug=slug, state=Enum__Instance__State.UNKNOWN)
        region     = str(entry.region)
        stack_name = str(entry.stack_name)
        ec2        = self._ec2_client(region)
        instance   = self._find_instance(ec2, stack_name)
        if not instance:
            return Schema__Endpoint__Resolution(
                slug=slug, region=region, state=Enum__Instance__State.UNKNOWN)
        iid      = instance.get('InstanceId', '')
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
        entry = self._find_region_for_instance(instance_id)
        region = entry.region if entry else 'eu-west-2'
        try:
            self._ec2_client(region).start_instances(InstanceIds=[instance_id])
            return True
        except Exception:
            return False

    def _find_instance(self, ec2, stack_name: str) -> Optional[dict]:
        resp = ec2.describe_instances(Filters=[
            {'Name': 'tag:StackName', 'Values': [stack_name]},
            {'Name': 'tag:StackType', 'Values': ['vault-app']},
            {'Name': 'instance-state-name', 'Values': ['running', 'stopped', 'pending', 'stopping']},
        ])
        for reservation in resp.get('Reservations', []):
            instances = reservation.get('Instances', [])
            if instances:
                return instances[0]
        return None

    def _find_region_for_instance(self, instance_id: str):
        return None                                                                 # Not needed when region is known from slug entry

    def _parse_state(self, raw: str) -> Enum__Instance__State:
        try:
            return Enum__Instance__State(raw)
        except ValueError:
            return Enum__Instance__State.UNKNOWN
