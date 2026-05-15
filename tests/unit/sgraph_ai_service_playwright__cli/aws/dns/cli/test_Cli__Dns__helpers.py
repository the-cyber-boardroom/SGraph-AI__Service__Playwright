# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Cli__Dns module-level helpers
# Regression coverage for the FQDN-aware zone resolution introduced after the
# `sg aws dns records check test.sg-compute.sgraph.ai` bug (CLI was defaulting
# to sgraph.ai instead of walking labels to the delegated sub-zone).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws.dns.cli.Cli__Dns                           import _resolve_zone_id, _resolve_zone_id_for_record
from sgraph_ai_service_playwright__cli.aws.dns.collections.List__Schema__Route53__Hosted_Zone import List__Schema__Route53__Hosted_Zone
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Route53__Hosted_Zone           import Schema__Route53__Hosted_Zone
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client                   import Route53__AWS__Client


_FAKE_ZONES_DATA = [                                                                 # Two parent + child zones mirroring the bug scenario
    {'zone_id': 'Z01SGRAPH'    , 'name': 'sgraph.ai'         , 'private_zone': False, 'record_count': 10, 'comment': '', 'caller_reference': 'r1'},
    {'zone_id': 'Z02SGCOMPUTE' , 'name': 'sg-compute.sgraph.ai', 'private_zone': False, 'record_count': 5 , 'comment': '', 'caller_reference': 'r2'},
]


class _Fake_Route53__AWS__Client(Route53__AWS__Client):

    def list_hosted_zones(self):
        zones = List__Schema__Route53__Hosted_Zone()
        for d in _FAKE_ZONES_DATA:
            zones.append(Schema__Route53__Hosted_Zone(**d))
        return zones

    def client(self):                                                                # Unused by these helpers — return None
        return None

    def resolve_zone_id(self, zone_id_or_name: str) -> str:                          # Bypass boto3 client; map name → id via the fake list
        token = zone_id_or_name.strip().rstrip('.')
        for d in _FAKE_ZONES_DATA:
            if token == d['zone_id'] or token == d['name']:
                return d['zone_id']
        raise ValueError(f"No hosted zone found with name '{zone_id_or_name}'")


class test_Cli__Dns__helpers(TestCase):

    def setUp(self):
        self.client = _Fake_Route53__AWS__Client()

    # ── _resolve_zone_id (unchanged behaviour — explicit or default) ──────────

    def test__resolve_zone_id__explicit_zone_used(self):
        assert _resolve_zone_id(self.client, 'sg-compute.sgraph.ai') == 'Z02SGCOMPUTE'

    def test__resolve_zone_id__no_zone_falls_back_to_default(self):
        assert _resolve_zone_id(self.client, '') == 'Z01SGRAPH'

    # ── _resolve_zone_id_for_record — the bug fix ─────────────────────────────

    def test__for_record__explicit_zone_wins(self):                                   # Explicit --zone always honoured
        assert _resolve_zone_id_for_record(self.client, 'sgraph.ai', 'test.sg-compute.sgraph.ai') == 'Z01SGRAPH'

    def test__for_record__sub_zone_fqdn_picks_deepest_zone(self):                     # The actual bug case
        assert _resolve_zone_id_for_record(self.client, '', 'test.sg-compute.sgraph.ai') == 'Z02SGCOMPUTE'

    def test__for_record__child_zone_apex_picks_child_zone(self):                     # Second bug: querying NS / SOA at sg-compute.sgraph.ai must hit Z02SGCOMPUTE
        assert _resolve_zone_id_for_record(self.client, '', 'sg-compute.sgraph.ai') == 'Z02SGCOMPUTE'

    def test__for_record__sub_zone_fqdn_with_trailing_dot(self):
        assert _resolve_zone_id_for_record(self.client, '', 'test.sg-compute.sgraph.ai.') == 'Z02SGCOMPUTE'

    def test__for_record__apex_fqdn_picks_apex_zone(self):
        assert _resolve_zone_id_for_record(self.client, '', 'www.sgraph.ai') == 'Z01SGRAPH'

    def test__for_record__bare_label_falls_back_to_default(self):                     # Single label → no FQDN walk → default
        assert _resolve_zone_id_for_record(self.client, '', 'localhost') == 'Z01SGRAPH'

    def test__for_record__unowned_fqdn_falls_back_to_default(self):                   # No matching zone → fall back instead of raising
        assert _resolve_zone_id_for_record(self.client, '', 'something.unowned.example') == 'Z01SGRAPH'
