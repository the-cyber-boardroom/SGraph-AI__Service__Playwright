# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: tests for the pure services
# Differ (state-transition events), Metrics (ring-buffer sparkline series),
# Comparison (local-vs-edge rows), Card (ASCII export). All pure — fed hand-built
# snapshots, asserted on outputs. No AWS, no Textual — runs on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.sg_edge.local.schemas.Schema__Local__Edge__Issue       import Schema__Local__Edge__Issue
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Event_Kind        import Enum__SG_Edge__TUI__Event_Kind
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State        import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Sync_State        import Enum__SG_Edge__TUI__Sync_State
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Slug          import Schema__SG_Edge__TUI__Slug
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot      import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.service.SG_Edge__TUI__Differ                import SG_Edge__TUI__Differ
from sg_compute_specs.sg_edge.tui.service.SG_Edge__TUI__Metrics               import SG_Edge__TUI__Metrics
from sg_compute_specs.sg_edge.tui.service.SG_Edge__TUI__Comparison            import SG_Edge__TUI__Comparison
from sg_compute_specs.sg_edge.tui.service.SG_Edge__TUI__Card                  import SG_Edge__TUI__Card

LIVE    = Enum__SG_Edge__TUI__Slug_State.LIVE
DORMANT = Enum__SG_Edge__TUI__Slug_State.DORMANT


def snap(slugs=(), fleet=(), issues=(), ts=100, parent='p'):
    s = Schema__SG_Edge__TUI__Snapshot(parent=parent, captured_at=ts, zone_exists=True, wildcard=True)
    for name, state in slugs:
        s.slugs.append(Schema__SG_Edge__TUI__Slug(slug=name, fqdn=f'{name}.{parent}', state=state))
    for ip in fleet:
        s.fleet_ips.append(ip)
    for area, message in issues:
        s.issues.append(Schema__Local__Edge__Issue(area=area, message=message))
    return s


class test_SG_Edge__TUI__Differ(TestCase):

    def setUp(self):
        self.differ = SG_Edge__TUI__Differ()

    def kinds(self, prev, curr):
        return [e.kind for e in self.differ.diff(prev, curr)]

    def test_first_snapshot__no_events(self):
        assert list(self.differ.diff(None, snap([('a', LIVE)]))) == []

    def test_slug_registered_and_removed(self):
        assert self.kinds(snap([('a', LIVE)]), snap([('a', LIVE), ('b', DORMANT)])) == [Enum__SG_Edge__TUI__Event_Kind.SLUG_REGISTERED]
        assert self.kinds(snap([('a', LIVE), ('b', DORMANT)]), snap([('a', LIVE)])) == [Enum__SG_Edge__TUI__Event_Kind.REMOVED]

    def test_went_live_and_went_dormant(self):
        assert self.kinds(snap([('a', DORMANT)]), snap([('a', LIVE)]))    == [Enum__SG_Edge__TUI__Event_Kind.WENT_LIVE]
        assert self.kinds(snap([('a', LIVE)]),    snap([('a', DORMANT)])) == [Enum__SG_Edge__TUI__Event_Kind.WENT_DORMANT]

    def test_fleet_change(self):
        assert self.kinds(snap(fleet=['1']), snap(fleet=['1', '2'])) == [Enum__SG_Edge__TUI__Event_Kind.FLEET_CHANGED]

    def test_issue_appeared_and_cleared(self):
        kinds = self.kinds(snap(issues=[('x', 'm1')]), snap(issues=[('x', 'm2')]))
        assert Enum__SG_Edge__TUI__Event_Kind.ISSUE   in kinds
        assert Enum__SG_Edge__TUI__Event_Kind.CLEARED in kinds

    def test_event_carries_capture_ts(self):
        events = self.differ.diff(snap([], ts=1), snap([('a', LIVE)], ts=999))
        assert all(int(e.ts) == 999 for e in events)


class test_SG_Edge__TUI__Metrics(TestCase):

    def test_ring_buffer_trims_to_max_points(self):
        m = SG_Edge__TUI__Metrics(max_points=3)
        for n in range(5):
            m.record(snap([(f's{i}', LIVE) for i in range(n)]))
        assert len(m.total_slugs)        == 3
        assert m.values(m.total_slugs)   == [2, 3, 4]                                 # last 3 of 0,1,2,3,4

    def test_live_count_excludes_dormant(self):
        m = SG_Edge__TUI__Metrics()
        m.record(snap([('a', LIVE), ('b', DORMANT), ('c', LIVE)]))
        assert m.values(m.total_slugs) == [3]
        assert m.values(m.live_slugs)  == [2]

    def test_fleet_series(self):
        m = SG_Edge__TUI__Metrics()
        m.record(snap(fleet=['1', '2']))
        assert m.values(m.fleet_size) == [2]


class test_SG_Edge__TUI__Comparison(TestCase):

    def test_compare__sync_states(self):
        local = snap(slugs=[('a', LIVE), ('b', LIVE)], fleet=['1'])
        aws   = snap(slugs=[('a', LIVE), ('c', LIVE)], fleet=[])
        rows  = {r.name: r.sync_state for r in SG_Edge__TUI__Comparison().compare(local, aws)}
        assert rows['wildcard']    == Enum__SG_Edge__TUI__Sync_State.IN_SYNC           # both True
        assert rows['proxy fleet'] == Enum__SG_Edge__TUI__Sync_State.LOCAL_ONLY        # local has, aws empty
        assert rows['slug:a']      == Enum__SG_Edge__TUI__Sync_State.IN_SYNC
        assert rows['slug:b']      == Enum__SG_Edge__TUI__Sync_State.LOCAL_ONLY
        assert rows['slug:c']      == Enum__SG_Edge__TUI__Sync_State.EDGE_ONLY


class test_SG_Edge__TUI__Card(TestCase):

    def test_render__not_provisioned(self):
        s             = snap(parent='edge.sg-labs.local')
        s.zone_exists = False
        out           = SG_Edge__TUI__Card().render(s)
        assert 'not provisioned' in out

    def test_render__provisioned_states_pending_and_slug(self):
        s   = snap(slugs=[('alice', LIVE)], fleet=['10.0.0.1'], parent='edge.sg-labs.app')
        out = SG_Edge__TUI__Card().render(s)
        assert 'SG/Edge'          in out
        assert 'edge.sg-labs.app' in out
        assert 'alice'            in out
        assert 'pending'          in out                                              # honesty: pending panes are named, not faked

    def test_render__includes_checks(self):
        s   = snap(issues=[('wildcard', 'missing')], parent='p')
        out = SG_Edge__TUI__Card().render(s)
        assert 'Checks:' in out
        assert 'missing' in out
