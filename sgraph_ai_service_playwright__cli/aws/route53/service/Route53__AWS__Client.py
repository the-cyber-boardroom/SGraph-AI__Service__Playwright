# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Route53__AWS__Client
# Sole boto3 boundary for Route53 A-record upserts.
# Handles DNS lifecycle for ephemeral Fargate tasks (dns_zone feature).
#
# Credentials resolved via Sg__Aws__Session so `sg credentials switch` is
# honoured. Subclasses override client() to inject fakes for unit tests.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Session import Sg__Aws__Session


class Route53__AWS__Client(Type_Safe):
    region  : str              = ''                                               # unused by Route53 (global service) — kept for interface parity
    session : Sg__Aws__Session = None                                             # cached session — injected or lazy-init via setup()

    def setup(self):                                                               # idempotent — noop if session already set
        if self.session is None:
            self.session = Sg__Aws__Session.from_context()
        return self

    def client(self):                                                              # single boto3 seam — subclass overrides for tests
        self.setup()
        return self.session.boto3_client_from_context('route53', region=self.region)

    # ── record mutations ──────────────────────────────────────────────────────

    def upsert_a_record(self, hosted_zone_id: str, fqdn: str,
                        ip: str, ttl: int = 60) -> bool:                          # create-or-replace A record; returns True on success
        try:
            r53 = self.client()
            r53.change_resource_record_sets(
                HostedZoneId = hosted_zone_id,
                ChangeBatch  = {
                    'Changes': [{
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name'           : fqdn,
                            'Type'           : 'A',
                            'TTL'            : ttl,
                            'ResourceRecords': [{'Value': ip}],
                        },
                    }]
                },
            )
            return True
        except Exception:
            return False

    def delete_a_record(self, hosted_zone_id: str, fqdn: str,
                        ip: str, ttl: int = 60) -> bool:                          # delete A record; returns False if not found
        try:
            r53 = self.client()
            r53.change_resource_record_sets(
                HostedZoneId = hosted_zone_id,
                ChangeBatch  = {
                    'Changes': [{
                        'Action': 'DELETE',
                        'ResourceRecordSet': {
                            'Name'           : fqdn,
                            'Type'           : 'A',
                            'TTL'            : ttl,
                            'ResourceRecords': [{'Value': ip}],
                        },
                    }]
                },
            )
            return True
        except Exception as exc:
            if 'InvalidChangeBatch' in str(type(exc).__name__) or 'InvalidChangeBatch' in str(exc):
                return False
            return False

    def find_hosted_zone_id(self, dns_zone: str) -> str:                          # returns bare zone id (no /hostedzone/ prefix) or ''
        try:
            r53  = self.client()
            resp = r53.list_hosted_zones_by_name(DNSName=dns_zone)
            for zone in resp.get('HostedZones', []):
                zone_name = zone.get('Name', '').rstrip('.')
                target    = dns_zone.rstrip('.')
                if zone_name == target:
                    raw_id = zone.get('Id', '')
                    return raw_id.replace('/hostedzone/', '')
            return ''
        except Exception:
            return ''
