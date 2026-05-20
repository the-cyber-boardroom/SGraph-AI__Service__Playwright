# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge: tests for SG_Edge__DNS__Helper
# Exercises the helper against the real Route53__AWS__Client logic via the
# dict-backed Route53__AWS__Client__In_Memory fake (no mocks, no patches).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from tests.unit.sgraph_ai_service_playwright__cli.aws.dns.service.Route53__AWS__Client__In_Memory import Route53__AWS__Client__In_Memory
from sg_compute_specs.sg_edge.schemas.Schema__SG_Edge__State__Record import Schema__SG_Edge__State__Record
from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper           import SG_Edge__DNS__Helper

PARENT = 'cv.sgraph.ai'


class test_SG_Edge__DNS__Helper(TestCase):

    def setUp(self):
        self.r53 = Route53__AWS__Client__In_Memory()
        self.r53.seed_zone(PARENT)
        self.helper = SG_Edge__DNS__Helper(route53=self.r53)

    # ── record-name composition ────────────────────────────────────────────────

    def test_record_names(self):
        assert self.helper.proxies_name(PARENT)         == 'proxies.cv.sgraph.ai'
        assert self.helper.state_name(PARENT)           == '_state.cv.sgraph.ai'
        assert self.helper.routing_name(PARENT, 'alice') == '_sg.alice.cv.sgraph.ai'

    # ── proxy fleet membership ──────────────────────────────────────────────────

    def test_proxy_membership__starts_empty(self):
        assert self.helper.list_proxy_ips(PARENT) == []
        assert self.helper.proxy_count(PARENT)    == 0

    def test_add_proxy_ip__is_idempotent(self):
        assert self.helper.add_proxy_ip(PARENT, '1.2.3.4') is not None
        assert self.helper.add_proxy_ip(PARENT, '1.2.3.4') is None             # already present -> no-op
        assert self.helper.proxy_count(PARENT) == 1
        assert self.helper.list_proxy_ips(PARENT) == ['1.2.3.4']

    def test_add_proxy_ip__multiple(self):
        self.helper.add_proxy_ip(PARENT, '1.2.3.4')
        self.helper.add_proxy_ip(PARENT, '1.2.3.5')
        assert self.helper.proxy_count(PARENT)         == 2
        assert set(self.helper.list_proxy_ips(PARENT)) == {'1.2.3.4', '1.2.3.5'}

    def test_remove_proxy_ip__shrinks_set(self):
        self.helper.add_proxy_ip(PARENT, '1.2.3.4')
        self.helper.add_proxy_ip(PARENT, '1.2.3.5')
        self.helper.remove_proxy_ip(PARENT, '1.2.3.4')
        assert self.helper.list_proxy_ips(PARENT) == ['1.2.3.5']

    def test_remove_proxy_ip__last_one_deletes_record(self):
        self.helper.add_proxy_ip(PARENT, '1.2.3.4')
        self.helper.remove_proxy_ip(PARENT, '1.2.3.4')
        assert self.helper.proxy_count(PARENT) == 0
        assert self.r53.record_exists(PARENT, 'proxies.cv.sgraph.ai', 'A') is False

    def test_remove_proxy_ip__absent_is_noop(self):
        assert self.helper.remove_proxy_ip(PARENT, '9.9.9.9') is None

    # ── teardown counter (_state TXT) ───────────────────────────────────────────

    def test_read_state__absent_returns_zeroed(self):
        state = self.helper.read_state(PARENT)
        assert int(state.zero_streak) == 0
        assert int(state.updated)     == 0

    def test_write_then_read_state(self):
        self.helper.write_state(PARENT, Schema__SG_Edge__State__Record(zero_streak=2, updated=1747700000))
        state = self.helper.read_state(PARENT)
        assert int(state.zero_streak) == 2
        assert int(state.updated)     == 1747700000

    def test_write_state__overwrites(self):
        self.helper.write_state(PARENT, Schema__SG_Edge__State__Record(zero_streak=2, updated=1))
        self.helper.write_state(PARENT, Schema__SG_Edge__State__Record(zero_streak=0, updated=9))
        state = self.helper.read_state(PARENT)
        assert int(state.zero_streak) == 0
        assert int(state.updated)     == 9

    # ── active vaults (_sg.* TXT, read-only) ─────────────────────────────────────

    def _seed_routing(self, slug, txt='v=1;ip=10.0.1.5;port=8080;type=ec2;launched=1747700000'):
        self.r53.seed_record(PARENT, f'_sg.{slug}.{PARENT}', 'TXT', [f'"{txt}"'])

    def test_active_slugs__counts_only_sg_txt(self):
        self._seed_routing('alice')
        self._seed_routing('bob')
        self.helper.write_state(PARENT, Schema__SG_Edge__State__Record(zero_streak=1, updated=1))  # _state TXT must not count
        self.helper.add_proxy_ip(PARENT, '1.2.3.4')                                                # proxies A must not count
        assert set(self.helper.list_active_slugs(PARENT)) == {'alice', 'bob'}
        assert self.helper.active_slug_count(PARENT)       == 2

    def test_active_slugs__empty(self):
        assert self.helper.list_active_slugs(PARENT) == []

    def test_read_routing__parses_record(self):
        self._seed_routing('alice')
        record = self.helper.read_routing(PARENT, 'alice')
        assert record is not None
        assert str(record.ip)   == '10.0.1.5'
        assert int(record.port) == 8080

    def test_read_routing__absent_returns_none(self):
        assert self.helper.read_routing(PARENT, 'ghost') is None

    def test_read_routing__malformed_returns_none(self):
        self.r53.seed_record(PARENT, '_sg.broken.cv.sgraph.ai', 'TXT', ['"not a valid record"'])
        assert self.helper.read_routing(PARENT, 'broken') is None
