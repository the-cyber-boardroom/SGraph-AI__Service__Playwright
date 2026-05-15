# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Route53__AWS__Client
# Sole boto3 boundary for Route 53 operations. Every boto3 call for the
# dns sub-package lives here so Cli__Dns can stay pure Python + Type_Safe
# schemas and the in-memory test subclass has a small, well-defined surface.
#
# FOLLOW-UP: the rest of the repo forbids direct boto3 use (CLAUDE.md rule)
# and routes AWS operations through osbot-aws. No osbot-aws Route 53 wrapper
# exists at the time of writing. Keeping the entire client on raw boto3 gives
# us one import boundary, matching the Elastic__AWS__Client precedent. Migrate
# to osbot-aws once a Route 53 wrapper is available there.
#
# P0 surface: read-only (list_hosted_zones, find_hosted_zone_by_name,
# resolve_default_zone, get_hosted_zone, list_records, get_record).
# P1 surface: mutations (create_record, upsert_record, delete_record,
# upsert_a_alias_record) plus the shared _change_rrset helper.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                          import Optional

import boto3                                                                         # EXCEPTION — see module header

from osbot_utils.type_safe.Type_Safe                                                 import Type_Safe
from osbot_utils.type_safe.type_safe_core.decorators.type_safe                       import type_safe

from sgraph_ai_service_playwright__cli.aws.dns.collections.List__Schema__Route53__Hosted_Zone import List__Schema__Route53__Hosted_Zone
from sgraph_ai_service_playwright__cli.aws.dns.collections.List__Schema__Route53__Record      import List__Schema__Route53__Record
from sgraph_ai_service_playwright__cli.aws.dns.enums.Enum__Route53__Record_Type               import Enum__Route53__Record_Type
from sgraph_ai_service_playwright__cli.aws.dns.primitives.Safe_Str__Hosted_Zone_Id            import Safe_Str__Hosted_Zone_Id
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Route53__Change__Result        import Schema__Route53__Change__Result
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Route53__Hosted_Zone           import Schema__Route53__Hosted_Zone
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Route53__Record                import Schema__Route53__Record

DEFAULT_ZONE_NAME = 'sgraph.ai'                                                      # Default zone for the sg aws dns CLI surface when --zone is not passed


class Route53__AWS__Client(Type_Safe):                                               # Isolated boto3 boundary for Route 53 read operations

    _default_zone : Optional[Schema__Route53__Hosted_Zone] = None                    # Cached result of resolve_default_zone() — one lookup per process

    def client(self):                                                                 # Single seam — tests override to return a fake client
        return boto3.client('route53')

    def list_hosted_zones(self) -> List__Schema__Route53__Hosted_Zone:               # Paginate all hosted zones in the account; returns typed list
        r53   = self.client()
        zones = List__Schema__Route53__Hosted_Zone()
        paginator = r53.get_paginator('list_hosted_zones')
        for page in paginator.paginate():
            for raw in page.get('HostedZones', []):
                zone = self.map_hosted_zone(raw)
                zones.append(zone)
        return zones

    def map_hosted_zone(self, raw: dict) -> Schema__Route53__Hosted_Zone:            # Map a raw boto3 HostedZone dict to Schema__Route53__Hosted_Zone
        zone_id_raw  = raw.get('Id', '')
        zone_id      = zone_id_raw.replace('/hostedzone/', '')                       # Strip the /hostedzone/ prefix that Route 53 returns
        name_raw     = raw.get('Name', '')
        name         = name_raw.rstrip('.')                                           # Strip trailing dot — Route 53 always appends one
        config       = raw.get('Config', {})
        comment      = config.get('Comment', '')
        private_zone = bool(config.get('PrivateZone', False))
        record_count = int(raw.get('ResourceRecordSetCount', 0))
        caller_ref   = raw.get('CallerReference', '')
        return Schema__Route53__Hosted_Zone(zone_id         = zone_id        ,
                                            name            = name           ,
                                            private_zone    = private_zone   ,
                                            record_count    = record_count   ,
                                            comment         = comment        ,
                                            caller_reference= caller_ref     )

    def find_hosted_zone_by_name(self, name: str) -> Optional[Schema__Route53__Hosted_Zone]:  # Search list_hosted_zones for an exact name match (with or without trailing dot)
        target = name.rstrip('.')                                                     # Normalise for comparison — strip trailing dot from the target
        for zone in self.list_hosted_zones():
            zone_name = str(zone.name).rstrip('.')
            if zone_name == target:
                return zone
        return None

    def resolve_default_zone(self) -> Schema__Route53__Hosted_Zone:                  # Lookup sgraph.ai; cache the result; raise ValueError when not found
        if self._default_zone is None:
            zone = self.find_hosted_zone_by_name(DEFAULT_ZONE_NAME)
            if zone is None:
                raise ValueError(f"--zone unset and no '{DEFAULT_ZONE_NAME}' hosted zone found in account")
            self._default_zone = zone
        return self._default_zone

    @type_safe
    def get_hosted_zone(self, zone_id_or_name: str) -> Schema__Route53__Hosted_Zone:  # Resolve by id or by name; id lookup uses boto3 get_hosted_zone; name lookup calls find_hosted_zone_by_name
        zone_id_or_name = zone_id_or_name.strip()
        if zone_id_or_name.startswith('/hostedzone/') or zone_id_or_name.startswith('Z'):
            raw_id = zone_id_or_name.replace('/hostedzone/', '')
            r53    = self.client()
            resp   = r53.get_hosted_zone(Id=raw_id)
            raw    = resp.get('HostedZone', {})
            return self.map_hosted_zone(raw)
        zone = self.find_hosted_zone_by_name(zone_id_or_name)
        if zone is None:
            raise ValueError(f"No hosted zone found with name '{zone_id_or_name}'")
        return zone

    def resolve_zone_id(self, zone_id_or_name: str) -> str:                          # Convenience: get the bare zone id from either an id or a name
        zone_id_or_name = zone_id_or_name.strip()
        if zone_id_or_name.startswith('/hostedzone/'):
            return zone_id_or_name.replace('/hostedzone/', '')
        if zone_id_or_name.startswith('Z'):
            return zone_id_or_name
        zone = self.find_hosted_zone_by_name(zone_id_or_name)
        if zone is None:
            raise ValueError(f"No hosted zone found with name '{zone_id_or_name}'")
        return str(zone.zone_id)

    @type_safe
    def list_records(self, zone_id_or_name: str) -> List__Schema__Route53__Record:   # Paginate all resource record sets in the zone; alias records get alias_target populated; ttl=0 for aliases
        zone_id = self.resolve_zone_id(zone_id_or_name)
        r53     = self.client()
        records = List__Schema__Route53__Record()
        paginator = r53.get_paginator('list_resource_record_sets')
        for page in paginator.paginate(HostedZoneId=zone_id):
            for rrs in page.get('ResourceRecordSets', []):
                record = self.map_record(rrs)
                records.append(record)
        return records

    def map_record(self, rrs: dict) -> Schema__Route53__Record:                      # Map a raw ResourceRecordSet dict to Schema__Route53__Record
        name           = str(rrs.get('Name', ''))
        rtype          = str(rrs.get('Type', 'A'))
        ttl            = int(rrs.get('TTL', 0))
        set_identifier = str(rrs.get('SetIdentifier', ''))
        alias_raw      = rrs.get('AliasTarget')
        alias_target   = str(alias_raw.get('DNSName', '')) if alias_raw else ''
        raw_values     = rrs.get('ResourceRecords', [])
        values         = [str(rv.get('Value', '')) for rv in raw_values]
        try:
            record_type = Enum__Route53__Record_Type(rtype)
        except ValueError:                                                            # Unknown type from Route 53 — fall back to A to avoid a crash
            record_type = Enum__Route53__Record_Type.A
        return Schema__Route53__Record(name           = name          ,
                                       record_type    = record_type   ,
                                       ttl            = ttl           ,
                                       values         = values        ,
                                       alias_target   = alias_target  ,
                                       set_identifier = set_identifier)

    @type_safe
    def get_record(self, zone_id_or_name    : str                       ,
                         name              : str                       ,
                         record_type       : Enum__Route53__Record_Type = Enum__Route53__Record_Type.A
                   ) -> Optional[Schema__Route53__Record]:              # Filter list_records by name + type; returns None when not found
        target_name = name.rstrip('.')                                               # Normalise for comparison
        target_type = str(record_type)
        for record in self.list_records(zone_id_or_name):
            record_name = str(record.name).rstrip('.')
            if record_name == target_name and str(record.record_type) == target_type:
                return record
        return None

    # ── P1: Mutation methods ──────────────────────────────────────────────────

    def _change_rrset(self, zone_id: str, action: str,
                      name: str, rtype: str, values: list,
                      ttl: int = None, alias_target: dict = None) -> Schema__Route53__Change__Result:  # Build the Change batch and call change_resource_record_sets
        r53 = self.client()
        if alias_target:
            rrset = {'Name': name, 'Type': rtype, 'AliasTarget': alias_target}
        else:
            rrset = {'Name': name, 'Type': rtype, 'TTL': ttl,
                     'ResourceRecords': [{'Value': v} for v in values]}
        change = {'Action': action, 'ResourceRecordSet': rrset}
        resp   = r53.change_resource_record_sets(
            HostedZoneId = zone_id,
            ChangeBatch  = {'Changes': [change]},
        )
        info   = resp.get('ChangeInfo', {})
        return Schema__Route53__Change__Result(
            change_id    = info.get('Id', '')         ,
            status       = info.get('Status', '')     ,
            submitted_at = str(info.get('SubmittedAt', '')),
        )

    def create_record(self, zone_id_or_name: str, name: str,
                      record_type: Enum__Route53__Record_Type,
                      values: list, ttl: int = 60) -> Schema__Route53__Change__Result:  # CREATE action; raises ValueError if record already exists
        zone_id  = self.resolve_zone_id(zone_id_or_name)
        existing = self.get_record(zone_id, name, record_type)
        if existing is not None:
            raise ValueError(
                f"Record '{name}' ({record_type}) already exists in zone {zone_id}. "
                "Use upsert_record (or `records update` CLI) to change it."
            )
        return self._change_rrset(zone_id, 'CREATE', name, str(record_type), values, ttl=ttl)

    def upsert_record(self, zone_id_or_name: str, name: str,
                      record_type: Enum__Route53__Record_Type,
                      values: list, ttl: int = 60) -> Schema__Route53__Change__Result:  # UPSERT action — creates or replaces
        zone_id = self.resolve_zone_id(zone_id_or_name)
        return self._change_rrset(zone_id, 'UPSERT', name, str(record_type), values, ttl=ttl)

    def delete_record(self, zone_id_or_name: str, name: str,
                      record_type: Enum__Route53__Record_Type,
                      values: list = None, ttl: int = None) -> Schema__Route53__Change__Result:  # DELETE action; fetches current values/ttl if not supplied
        zone_id  = self.resolve_zone_id(zone_id_or_name)
        existing = self.get_record(zone_id, name, record_type)
        if existing is None:
            raise ValueError(f"Record '{name}' ({record_type}) not found in zone {zone_id}.")
        actual_values = values if values is not None else list(existing.values)
        actual_ttl    = ttl    if ttl    is not None else int(existing.ttl)
        return self._change_rrset(zone_id, 'DELETE', name, str(record_type), actual_values, ttl=actual_ttl)

    def upsert_a_alias_record(self, zone_id_or_name: str, name: str,
                               alias_dns_name: str, alias_zone_id: str) -> Schema__Route53__Change__Result:  # UPSERT A alias record (no TTL field — Route 53 manages it)
        zone_id      = self.resolve_zone_id(zone_id_or_name)
        alias_target = {'DNSName': alias_dns_name, 'HostedZoneId': alias_zone_id,
                        'EvaluateTargetHealth': False}
        return self._change_rrset(zone_id, 'UPSERT', name, 'A', [], alias_target=alias_target)
