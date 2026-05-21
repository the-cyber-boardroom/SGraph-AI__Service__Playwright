# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: tests for the Screen-5 render (pure)
# Asserts the sparkline mapping and the event feed (filtering, paused tag, the honest
# "observed transitions / not rps" labels). No textual — runs on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Event_Kind        import Enum__SG_Edge__TUI__Event_Kind
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State        import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Event         import Schema__SG_Edge__TUI__Event
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Slug          import Schema__SG_Edge__TUI__Slug
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot      import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.service.SG_Edge__TUI__Metrics               import SG_Edge__TUI__Metrics
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Events__Render        import events_markup, sparkline

EK   = Enum__SG_Edge__TUI__Event_Kind
LIVE = Enum__SG_Edge__TUI__Slug_State.LIVE


def snap(n_slugs=0):
    s = Schema__SG_Edge__TUI__Snapshot(parent='edge.sg-labs.local', captured_at=100, zone_exists=True)
    for i in range(n_slugs):
        s.slugs.append(Schema__SG_Edge__TUI__Slug(slug=f's{i}', fqdn=f's{i}.x', state=LIVE))
    return s


def event(kind, detail, ts=1747700000):
    return Schema__SG_Edge__TUI__Event(kind=kind, detail=detail, ts=ts)


class test_sparkline(TestCase):

    def test_empty(self):
        assert sparkline([]) == ''

    def test_flat(self):
        assert sparkline([3, 3, 3]) == '▁▁▁'

    def test_full_range(self):
        assert sparkline([0, 1, 2, 3, 4, 5, 6, 7]) == '▁▂▃▄▅▆▇█'


class test_events_markup(TestCase):

    def setUp(self):
        self.metrics = SG_Edge__TUI__Metrics()
        for n in (1, 2, 3):
            self.metrics.record(snap(n))
        self.events = [event(EK.FLEET_CHANGED, 'proxy fleet 1 → 2'),
                       event(EK.SLUG_REGISTERED, 'alice registered'),
                       event(EK.ISSUE, 'wildcard: missing')]

    def test_feed_and_sparklines(self):
        out = events_markup(snap(3), self.events, self.metrics, 'all', paused=False)
        assert 'Live Activity'    in out
        assert 'alice registered' in out
        assert 'proxy fleet 1 → 2' in out
        assert 'THROUGHPUT'       in out
        assert 'not rps'          in out                                             # honest sparkline label
        assert sparkline(self.metrics.values(self.metrics.total_slugs)) in out

    def test_filter_slugs_hides_fleet_and_issues(self):
        out = events_markup(snap(3), self.events, self.metrics, 'slugs', paused=False)
        assert 'alice registered'  in out
        assert 'proxy fleet 1 → 2' not in out                                        # fleet event filtered out
        assert 'wildcard: missing' not in out

    def test_paused_tag(self):
        out = events_markup(snap(3), self.events, self.metrics, 'all', paused=True)
        assert 'PAUSED' in out

    def test_empty_feed(self):
        out = events_markup(snap(0), [], self.metrics, 'all', paused=False)
        assert 'no events yet' in out
