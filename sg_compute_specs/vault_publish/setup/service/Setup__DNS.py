# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Setup__DNS
# Drift-check + upsert for the Route 53 wildcard CNAME record.
#
# Expected record: *.{zone}. CNAME → CF distribution domain name.
# The CF domain is read from the live CloudFront distribution for *.{zone},
# so Setup__CF must be created first.
#
# Mutation gate: SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1
# Delete gate:   SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1
# ═══════════════════════════════════════════════════════════════════════════════

import os
from typing import Callable, Optional

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sg_compute_specs.vault_publish.setup.collections.List__Schema__Setup__Issue import List__Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State             import Enum__Setup__State
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__Issue           import Schema__Setup__Issue
from sg_compute_specs.vault_publish.setup.schemas.Schema__Setup__DNS__Report     import Schema__Setup__DNS__Report


class Setup__DNS(Type_Safe):
    _r53_factory : Optional[Callable] = None
    _cf_factory  : Optional[Callable] = None

    def _r53(self):
        if self._r53_factory:
            return self._r53_factory()
        from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client import Route53__AWS__Client
        return Route53__AWS__Client()

    def _cf(self):
        if self._cf_factory:
            return self._cf_factory()
        from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__AWS__Client import CloudFront__AWS__Client
        return CloudFront__AWS__Client()

    # ── read ─────────────────────────────────────────────────────────────────

    def check(self, zone: str) -> Schema__Setup__DNS__Report:
        record_name = f'*.{zone}'
        issues      = List__Schema__Setup__Issue()
        r53         = self._r53()
        zone_obj    = r53.find_hosted_zone_by_name(zone)
        if not zone_obj:
            issues.append(Schema__Setup__Issue(
                severity='error', area='dns',
                message=f'hosted zone {zone!r} not found in Route 53'))
            return Schema__Setup__DNS__Report(
                state=Enum__Setup__State.ERROR, zone=zone, issues=issues)

        from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type import Enum__Route53__Record_Type
        record = r53.get_record(str(zone_obj.zone_id), record_name, Enum__Route53__Record_Type.CNAME)
        if not record:
            issues.append(Schema__Setup__Issue(
                severity='error', area='dns',
                message=f'no CNAME record for {record_name}'))
            return Schema__Setup__DNS__Report(
                state=Enum__Setup__State.MISSING, zone=zone,
                record_name=record_name, issues=issues)

        record_value = list(record.values)[0] if record.values else ''
        return Schema__Setup__DNS__Report(
            state        = Enum__Setup__State.OK,
            zone         = zone,
            record_name  = record_name,
            record_value = record_value,
            record_exists= True,
            issues       = issues,
        )

    def status(self, zone: str) -> dict:
        record_name = f'*.{zone}'
        r53         = self._r53()
        zone_obj    = r53.find_hosted_zone_by_name(zone)
        if not zone_obj:
            return {'zone': zone, 'hosted_zone': 'not found'}
        from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type import Enum__Route53__Record_Type
        record = r53.get_record(str(zone_obj.zone_id), record_name, Enum__Route53__Record_Type.CNAME)
        if not record:
            return {'zone': zone, 'record': record_name, 'exists': 'no'}
        record_value = list(record.values)[0] if record.values else ''
        return {
            'zone'        : zone,
            'record'      : record_name,
            'type'        : 'CNAME',
            'value'       : record_value,
            'ttl'         : str(record.ttl),
        }

    # ── mutations ─────────────────────────────────────────────────────────────

    def create(self, zone: str) -> Schema__Setup__DNS__Report:
        _require_mutations()
        record_name = f'*.{zone}'
        issues      = List__Schema__Setup__Issue()

        cf_dist = self._cf().find_distribution_by_alias(record_name)
        if not cf_dist:
            issues.append(Schema__Setup__Issue(
                severity='error', area='dns',
                message=f'CloudFront distribution for {record_name} not found — run `setup cf create` first'))
            return Schema__Setup__DNS__Report(
                state=Enum__Setup__State.ERROR, zone=zone, issues=issues)

        cf_domain = str(cf_dist.domain_name)
        r53       = self._r53()
        zone_obj  = r53.find_hosted_zone_by_name(zone)
        if not zone_obj:
            issues.append(Schema__Setup__Issue(
                severity='error', area='dns',
                message=f'hosted zone {zone!r} not found in Route 53'))
            return Schema__Setup__DNS__Report(
                state=Enum__Setup__State.ERROR, zone=zone, issues=issues)

        from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type import Enum__Route53__Record_Type
        r53.upsert_record(str(zone_obj.zone_id), record_name,
                          Enum__Route53__Record_Type.CNAME, [cf_domain], ttl=300)
        return self.check(zone)

    def delete(self, zone: str) -> bool:
        _require_deletes()
        record_name = f'*.{zone}'
        r53         = self._r53()
        zone_obj    = r53.find_hosted_zone_by_name(zone)
        if not zone_obj:
            return False
        try:
            from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type import Enum__Route53__Record_Type
            r53.delete_record(str(zone_obj.zone_id), record_name, Enum__Route53__Record_Type.CNAME)
            return True
        except Exception:
            return False


# ── gates ─────────────────────────────────────────────────────────────────────

def _require_mutations():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1 to allow DNS mutations')


def _require_deletes():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1 to allow DNS deletes')
