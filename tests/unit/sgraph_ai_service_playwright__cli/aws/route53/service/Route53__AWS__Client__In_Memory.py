# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Route53__AWS__Client__In_Memory
# Dict-backed fake for Route53 A-record operations. No mocks. No patches.
# Subclasses Route53__AWS__Client and overrides client() to return _Fake_R53.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.aws.route53.service.Route53__AWS__Client import Route53__AWS__Client

_TEST_ZONE_ID = 'TESTZONE123'
_TEST_ZONE    = 'sg-compute.sgraph.ai'


class _Fake_R53_Client:
    """Minimal boto3-alike Route53 client backed by in-memory dicts."""

    def __init__(self, records: dict, zones: dict):
        self._records = records   # (zone_id, fqdn) → ip
        self._zones   = zones     # zone_name → zone_id

    def change_resource_record_sets(self, HostedZoneId: str, ChangeBatch: dict, **kwargs):
        for change in ChangeBatch.get('Changes', []):
            action  = change.get('Action', '')
            rrset   = change.get('ResourceRecordSet', {})
            name    = rrset.get('Name', '').rstrip('.')
            rtype   = rrset.get('Type', '')
            rrs     = rrset.get('ResourceRecords', [])
            ip      = rrs[0]['Value'] if rrs else ''
            key     = (HostedZoneId, name)
            if action in ('UPSERT', 'CREATE'):
                self._records[key] = ip
            elif action == 'DELETE':
                if key not in self._records:
                    from botocore.exceptions import ClientError
                    raise ClientError(
                        {'Error': {'Code': 'InvalidChangeBatch',
                                   'Message': 'No record found to delete'}},
                        'ChangeResourceRecordSets',
                    )
                del self._records[key]
        return {'ChangeInfo': {'Id': '/change/C123', 'Status': 'PENDING',
                               'SubmittedAt': '2026-05-19T00:00:00Z'}}

    def list_hosted_zones_by_name(self, DNSName: str = '', **kwargs):
        zones = []
        for name, zone_id in self._zones.items():
            zones.append({
                'Id'    : f'/hostedzone/{zone_id}',
                'Name'  : f'{name}.',
                'Config': {'PrivateZone': False},
                'ResourceRecordSetCount': 0,
                'CallerReference': 'ref',
            })
        return {'HostedZones': zones, 'IsTruncated': False}


class Route53__AWS__Client__In_Memory(Route53__AWS__Client):

    def __init__(self):
        super().__init__()
        self._records = {}
        self._zones   = {_TEST_ZONE: _TEST_ZONE_ID}
        self._fake    = _Fake_R53_Client(self._records, self._zones)

    def client(self):
        return self._fake
