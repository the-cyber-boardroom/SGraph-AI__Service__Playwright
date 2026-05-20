# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge local: Local__Route53__Client
# A file-backed Route 53 client — the "local DNS server" for the local edge stack.
# Subclasses Route53__AWS__Client and overrides client() to return a JSON-file-
# backed boto-alike fake, so the SAME SG_Edge__DNS__Helper / reconciler logic runs
# unchanged against local DNS (no AWS, no mocks). State persists to disk so it
# survives between separate `sg edge local *` CLI processes.
#
# Mirrors the shape of tests/.../Route53__AWS__Client__In_Memory (CREATE / UPSERT /
# DELETE change batches + list paginators) but lives in production and saves every
# mutation to <dns_path>.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client import Route53__AWS__Client


class _Local_Paginator:                                                              # mirrors botocore paginator for list_hosted_zones
    def __init__(self, pages):
        self._pages = pages

    def paginate(self, **kwargs):
        return iter(self._pages)


class _Local_R53_Fake:                                                               # minimal boto3-alike Route 53 client backed by file-loaded dicts
    def __init__(self, zones: dict, records: dict, on_change):
        self._zones     = zones
        self._records   = records
        self._on_change = on_change                                                  # persist callback, fired after each mutation

    def get_paginator(self, operation):
        if operation == 'list_hosted_zones':
            return _Local_Paginator([{'HostedZones': list(self._zones.values())}])
        if operation == 'list_resource_record_sets':
            return self
        return _Local_Paginator([{}])

    def paginate(self, HostedZoneId: str = ''):                                      # invoked by the list_resource_record_sets paginator above
        yield {'ResourceRecordSets': list(self._records.get(HostedZoneId, []))}

    def get_hosted_zone(self, Id: str):
        zone_id = Id.replace('/hostedzone/', '')
        return {'HostedZone': self._zones.get(zone_id, {})}

    def change_resource_record_sets(self, HostedZoneId: str, ChangeBatch: dict):
        records = self._records.setdefault(HostedZoneId, [])

        def _norm(s: str) -> str:                                                    # Route 53 treats foo.example.com and foo.example.com. identically
            return str(s).rstrip('.')

        for change in ChangeBatch.get('Changes', []):
            action = change.get('Action', '')
            rrset  = change.get('ResourceRecordSet', {})
            name   = rrset.get('Name', '')
            rtype  = rrset.get('Type', '')
            if action == 'DELETE':
                for idx, existing in enumerate(records):
                    if _norm(existing.get('Name', '')) == _norm(name) and existing.get('Type', '') == rtype:
                        records.pop(idx)
                        break
            elif action in ('CREATE', 'UPSERT'):
                replaced = False
                for idx, existing in enumerate(records):
                    if _norm(existing.get('Name', '')) == _norm(name) and existing.get('Type', '') == rtype:
                        records[idx] = dict(rrset)
                        replaced = True
                        break
                if not replaced:
                    records.append(dict(rrset))
        self._on_change()
        return {'ChangeInfo': {'Id': '/change/CLOCAL0001', 'Status': 'INSYNC',
                               'SubmittedAt': '2026-05-20T00:00:00Z'}}


class Local__Route53__Client(Route53__AWS__Client):

    def __init__(self, dns_path: str = ''):
        super().__init__()
        self._dns_path = dns_path
        self._zones    = {}                                                          # zone_id → raw HostedZone dict
        self._records  = {}                                                          # zone_id → list[raw ResourceRecordSet dict]
        self._load()
        self._fake     = _Local_R53_Fake(self._zones, self._records, self._save)

    def client(self):
        return self._fake

    # ── persistence ─────────────────────────────────────────────────────────────

    def _load(self):
        if self._dns_path and os.path.isfile(self._dns_path):
            data = json.loads(open(self._dns_path).read() or '{}')
            self._zones.update(data.get('zones', {}))
            self._records.update(data.get('records', {}))

    def _save(self):
        if not self._dns_path:
            return
        os.makedirs(os.path.dirname(self._dns_path), exist_ok=True)
        with open(self._dns_path, 'w') as f:
            f.write(json.dumps({'zones': self._zones, 'records': self._records}, indent=2))

    # ── zone bootstrap ────────────────────────────────────────────────────────────

    def ensure_zone(self, name: str) -> str:                                         # idempotent — create the hosted zone if absent; returns zone_id
        for zone_id, raw in self._zones.items():
            if raw.get('Name', '').rstrip('.') == name.rstrip('.'):
                return zone_id
        zone_id = f'Z{abs(hash(name)) % (10**10):010d}'
        self._zones[zone_id] = {
            'Id'                    : f'/hostedzone/{zone_id}',
            'Name'                  : name if name.endswith('.') else f'{name}.',
            'Config'                : {'Comment': 'sg-edge local', 'PrivateZone': False},
            'ResourceRecordSetCount': 0,
            'CallerReference'       : f'ref-{zone_id}',
        }
        self._records.setdefault(zone_id, [])
        self._save()
        return zone_id
