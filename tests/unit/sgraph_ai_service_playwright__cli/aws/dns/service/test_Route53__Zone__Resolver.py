# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for Route53__Zone__Resolver
# Fakes Route53__AWS__Client to provide a controlled set of zones.
# Tests: deepest-zone matching walks labels correctly; ValueError when no match.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

import pytest

from sgraph_ai_service_playwright__cli.aws.dns.collections.List__Schema__Route53__Hosted_Zone import List__Schema__Route53__Hosted_Zone
from sgraph_ai_service_playwright__cli.aws.dns.schemas.Schema__Route53__Hosted_Zone           import Schema__Route53__Hosted_Zone
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client                   import Route53__AWS__Client
from sgraph_ai_service_playwright__cli.aws.dns.service.Route53__Zone__Resolver                import Route53__Zone__Resolver


# ── Fake helpers ──────────────────────────────────────────────────────────────

_FAKE_ZONES_DATA = [
    {'zone_id': 'Z01SGRAPH', 'name': 'sgraph.ai'     , 'private_zone': False, 'record_count': 10, 'comment': '', 'caller_reference': 'r1'},
    {'zone_id': 'Z02DEV'   , 'name': 'dev.sgraph.ai' , 'private_zone': False, 'record_count': 5 , 'comment': '', 'caller_reference': 'r2'},
    {'zone_id': 'Z03STAGE' , 'name': 'stage.sgraph.ai', 'private_zone': False, 'record_count': 3, 'comment': '', 'caller_reference': 'r3'},
]


class _Fake_Route53__AWS__Client(Route53__AWS__Client):
    def list_hosted_zones(self):
        zones = List__Schema__Route53__Hosted_Zone()
        for d in _FAKE_ZONES_DATA:
            zones.append(Schema__Route53__Hosted_Zone(**d))
        return zones

    def client(self):
        return None


def _resolver() -> Route53__Zone__Resolver:
    return Route53__Zone__Resolver(r53_client=_Fake_Route53__AWS__Client())


# ── Tests ─────────────────────────────────────────────────────────────────────

class test_Route53__Zone__Resolver(TestCase):

    def test__resolve_zone_for_fqdn__matches_apex(self):
        r    = _resolver()
        zone = r.resolve_zone_for_fqdn('sgraph.ai')
        assert str(zone.zone_id) == 'Z01SGRAPH'

    def test__resolve_zone_for_fqdn__matches_direct_child(self):
        r    = _resolver()
        zone = r.resolve_zone_for_fqdn('www.sgraph.ai')
        assert str(zone.zone_id) == 'Z01SGRAPH'

    def test__resolve_zone_for_fqdn__prefers_deeper_zone(self):
        r    = _resolver()
        zone = r.resolve_zone_for_fqdn('my-ec2-1.dev.sgraph.ai')
        assert str(zone.zone_id) == 'Z02DEV'                                     # dev.sgraph.ai is deeper than sgraph.ai

    def test__resolve_zone_for_fqdn__stage_zone_resolved(self):
        r    = _resolver()
        zone = r.resolve_zone_for_fqdn('api.stage.sgraph.ai')
        assert str(zone.zone_id) == 'Z03STAGE'

    def test__resolve_zone_for_fqdn__apex_when_no_sub_zone(self):
        r    = _resolver()
        zone = r.resolve_zone_for_fqdn('prod.sgraph.ai')
        assert str(zone.zone_id) == 'Z01SGRAPH'

    def test__resolve_zone_for_fqdn__raises_when_no_zone_matches(self):
        r = _resolver()
        with pytest.raises(ValueError, match="No hosted zone"):
            r.resolve_zone_for_fqdn('example.com')

    def test__resolve_zone_for_fqdn__trailing_dot_ignored(self):
        r    = _resolver()
        zone = r.resolve_zone_for_fqdn('test.dev.sgraph.ai.')
        assert str(zone.zone_id) == 'Z02DEV'

    def test__resolve_zone_for_fqdn__caches_zones(self):
        r = _resolver()
        r.resolve_zone_for_fqdn('sgraph.ai')
        assert r._zone_cache                                                     # Cache populated after first call
        original_len = len(r._zone_cache)
        r.resolve_zone_for_fqdn('www.sgraph.ai')
        assert len(r._zone_cache) == original_len                                # Still same list — no re-fetch
