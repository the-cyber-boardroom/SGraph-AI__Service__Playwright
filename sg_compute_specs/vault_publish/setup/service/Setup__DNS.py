# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Setup__DNS
# Drift-check + upsert for the Route 53 wildcard DNS record.
#
# Route 53 supports two styles for *.{zone} → CloudFront routing:
#   CNAME  *.{zone} → d2n03kv7cxdjms.cloudfront.net
#   A ALIAS *.{zone} → d2n03kv7cxdjms.cloudfront.net  (recommended; no TTL)
#
# check() accepts either form as OK. create() uses CNAME (ALIAS requires the
# CloudFront hosted-zone ID which varies; CNAME is simpler and equally valid
# for non-apex names).
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

        record, rtype, rvalue = self._find_wildcard_record(r53, str(zone_obj.zone_id), record_name)
        if not record:
            issues.append(Schema__Setup__Issue(
                severity='error', area='dns',
                message=f'no wildcard record (CNAME or A alias) for {record_name}'))
            return Schema__Setup__DNS__Report(
                state=Enum__Setup__State.MISSING, zone=zone,
                record_name=record_name, issues=issues)

        return Schema__Setup__DNS__Report(
            state        = Enum__Setup__State.OK,
            zone         = zone,
            record_name  = record_name,
            record_value = rvalue,
            record_exists= True,
            issues       = issues,
        )

    def status(self, zone: str) -> dict:
        record_name = f'*.{zone}'
        r53         = self._r53()
        zone_obj    = r53.find_hosted_zone_by_name(zone)
        if not zone_obj:
            return {'zone': zone, 'hosted_zone': 'not found'}

        record, rtype, rvalue = self._find_wildcard_record(r53, str(zone_obj.zone_id), record_name)
        if not record:
            return {'zone': zone, 'record': record_name, 'exists': 'no'}
        return {
            'zone'  : zone,
            'record': record_name,
            'type'  : rtype,
            'value' : rvalue,
            'ttl'   : str(record.ttl),
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
        from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type import Enum__Route53__Record_Type
        for rtype in (Enum__Route53__Record_Type.CNAME, Enum__Route53__Record_Type.A):
            try:
                r53.delete_record(str(zone_obj.zone_id), record_name, rtype)
                return True
            except Exception:
                pass
        return False

    # ── internal ─────────────────────────────────────────────────────────────

    def _find_wildcard_record(self, r53, zone_id: str, record_name: str):
        """Return (record, type_str, value_str) for the first matching wildcard.

        Accepts CNAME or A-alias (Route 53 alias A records are the recommended
        form for CloudFront — they appear as type A with alias_target set).
        Returns (None, '', '') when no matching record is found.
        """
        from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type import Enum__Route53__Record_Type
        normalised = record_name.rstrip('.')
        for record in r53.list_records(zone_id):
            if str(record.name).rstrip('.') != normalised:
                continue
            if record.record_type == Enum__Route53__Record_Type.CNAME:
                value = list(record.values)[0] if record.values else ''
                return record, 'CNAME', value
            if record.record_type == Enum__Route53__Record_Type.A and record.alias_target:
                return record, 'A (alias)', record.alias_target.rstrip('.')
        return None, '', ''


# ── gates ─────────────────────────────────────────────────────────────────────

def _require_mutations():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1 to allow DNS mutations')


def _require_deletes():
    if not os.environ.get('SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES'):
        raise RuntimeError(
            'Set SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1 to allow DNS deletes')
