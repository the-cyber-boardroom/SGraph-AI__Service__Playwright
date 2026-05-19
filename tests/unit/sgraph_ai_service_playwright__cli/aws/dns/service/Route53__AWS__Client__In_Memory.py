# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Route53__AWS__Client__In_Memory
# Dict-backed fake boto3 Route 53 client for unit tests. No mocks. No patches.
# Subclasses Route53__AWS__Client and overrides client() to return _Fake_R53.
# Supports list_hosted_zones / list_resource_record_sets / change batches
# (CREATE / UPSERT / DELETE) — enough surface for vault-app DNS lifecycle tests.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client import Route53__AWS__Client


class _FakePaginator:                                                              # mirrors botocore paginator interface
    def __init__(self, pages):
        self._pages = pages

    def paginate(self, **kwargs):
        return iter(self._pages)


class _Fake_R53_Client:                                                            # minimal boto3-alike Route 53 client backed by in-memory dicts

    def __init__(self, zones: dict, records: dict):
        self._zones   = zones                                                       # zone_id → raw HostedZone dict
        self._records = records                                                     # zone_id → list[raw ResourceRecordSet dict]

    # ── reads ─────────────────────────────────────────────────────────────────

    def get_paginator(self, operation):
        if operation == 'list_hosted_zones':
            return _FakePaginator([{'HostedZones': list(self._zones.values())}])
        if operation == 'list_resource_record_sets':
            return self                                                             # use the bound paginate() below
        return _FakePaginator([{}])

    def paginate(self, HostedZoneId: str):                                          # invoked by list_resource_record_sets paginator above
        records = self._records.get(HostedZoneId, [])
        yield {'ResourceRecordSets': list(records)}

    def get_hosted_zone(self, Id: str):
        zone_id = Id.replace('/hostedzone/', '')
        raw     = self._zones.get(zone_id)
        if raw is None:
            for candidate in self._zones.values():
                if candidate.get('Id', '').replace('/hostedzone/', '') == zone_id:
                    raw = candidate
                    break
        return {'HostedZone': raw or {}}

    # ── mutations ─────────────────────────────────────────────────────────────

    def change_resource_record_sets(self, HostedZoneId: str, ChangeBatch: dict):
        records = self._records.setdefault(HostedZoneId, [])
        for change in ChangeBatch.get('Changes', []):
            action = change.get('Action', '')
            rrset  = change.get('ResourceRecordSet', {})
            name   = rrset.get('Name', '')
            rtype  = rrset.get('Type', '')
            if action == 'DELETE':                                                  # remove first match by name + type
                for idx, existing in enumerate(records):
                    if existing.get('Name', '') == name and existing.get('Type', '') == rtype:
                        records.pop(idx)
                        break
            elif action in ('CREATE', 'UPSERT'):                                    # replace existing or append
                replaced = False
                for idx, existing in enumerate(records):
                    if existing.get('Name', '') == name and existing.get('Type', '') == rtype:
                        records[idx] = dict(rrset)
                        replaced = True
                        break
                if not replaced:
                    records.append(dict(rrset))
        return {
            'ChangeInfo': {
                'Id'          : '/change/CFAKE0001',
                'Status'      : 'PENDING',
                'SubmittedAt' : '2026-05-19T00:00:00Z',
            }
        }


class Route53__AWS__Client__In_Memory(Route53__AWS__Client):

    def __init__(self):
        super().__init__()
        self._zones   = {}                                                          # zone_id → raw HostedZone dict
        self._records = {}                                                          # zone_id → list[raw ResourceRecordSet dict]
        self._fake    = _Fake_R53_Client(self._zones, self._records)

    def client(self):
        return self._fake

    # ── test helpers ──────────────────────────────────────────────────────────

    def seed_zone(self, name: str, zone_id: str = '') -> str:                       # add a hosted zone; returns zone_id
        zone_id = zone_id or f'Z{abs(hash(name)) % (10**10):010d}'
        raw_id  = zone_id if zone_id.startswith('/') else f'/hostedzone/{zone_id}'
        self._zones[zone_id] = {
            'Id'                    : raw_id,
            'Name'                  : name if name.endswith('.') else f'{name}.',
            'Config'                : {'Comment': '', 'PrivateZone': False},
            'ResourceRecordSetCount': 0,
            'CallerReference'       : f'ref-{zone_id}',
        }
        self._records.setdefault(zone_id, [])
        return zone_id

    def seed_record(self, zone_name: str, name: str, record_type: str = 'A',
                    values: list = None, ttl: int = 60) -> None:                    # add a record into a previously-seeded zone (by zone name)
        zone_id = self._zone_id_for_name(zone_name)
        if zone_id is None:
            zone_id = self.seed_zone(zone_name)
        fqdn = name if name.endswith('.') else f'{name}.'
        self._records.setdefault(zone_id, []).append({
            'Name'           : fqdn,
            'Type'           : record_type,
            'TTL'            : ttl,
            'ResourceRecords': [{'Value': v} for v in (values or [])],
        })

    def record_exists(self, zone_name: str, name: str, record_type: str = 'A') -> bool:  # convenience for assertions
        zone_id = self._zone_id_for_name(zone_name)
        if zone_id is None:
            return False
        fqdn = name if name.endswith('.') else f'{name}.'
        for r in self._records.get(zone_id, []):
            if r.get('Name', '') == fqdn and r.get('Type', '') == record_type:
                return True
        return False

    def _zone_id_for_name(self, zone_name: str):                                    # internal: zone_name → zone_id (None if not seeded)
        target = zone_name.rstrip('.')
        for zone_id, raw in self._zones.items():
            if raw.get('Name', '').rstrip('.') == target:
                return zone_id
        return None
