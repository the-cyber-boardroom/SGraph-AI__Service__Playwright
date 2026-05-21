# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: tests for the Screen-3 render (pure)
# Asserts the Local-vs-Edge markup + plain output and the drift summary. No textual,
# no rich — runs on 3.11. Honest two-way only (no Deployed column).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State        import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Slug          import Schema__SG_Edge__TUI__Slug
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot      import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Compare__Render       import compare_markup, compare_plain

LIVE = Enum__SG_Edge__TUI__Slug_State.LIVE


def snap(parent, slugs=(), fleet=(), wildcard=True, zone=True):
    s = Schema__SG_Edge__TUI__Snapshot(parent=parent, captured_at=100, zone_exists=zone, wildcard=wildcard)
    for name in slugs:
        s.slugs.append(Schema__SG_Edge__TUI__Slug(slug=name, fqdn=f'{name}.{parent}', state=LIVE))
    for ip in fleet:
        s.fleet_ips.append(ip)
    return s


class test_compare_render(TestCase):

    def setUp(self):
        self.local = snap('edge.sg-labs.local', slugs=['alice', 'bob'],   fleet=['127.0.0.1'])
        self.aws   = snap('edge.sg-labs.app',   slugs=['alice', 'carol'], fleet=[])

    def test_markup__rows_and_drift(self):
        out = compare_markup(self.local, self.aws)
        for token in ('Local vs Edge', 'wildcard', 'proxy fleet',
                      'slug:alice', 'slug:bob', 'slug:carol', 'DRIFT', 'local-only', 'edge-only'):
            assert token in out, token
        assert 'in sync'   in out                                                    # slug:alice + wildcard agree
        assert 'local only' in out                                                   # bob + proxy fleet
        assert 'edge only'  in out                                                   # carol

    def test_plain__has_no_markup_tags(self):
        out = compare_plain(self.local, self.aws)
        assert '[green]' not in out and '[bold]' not in out and '[dim]' not in out
        assert 'slug:carol' in out
        assert 'DRIFT'      in out

    def test_all_in_sync(self):
        same = snap('edge.sg-labs.app', slugs=['alice'], fleet=['10.0.0.1'])
        out  = compare_markup(same, snap('edge.sg-labs.app', slugs=['alice'], fleet=['10.0.0.1']))
        assert 'IN SYNC: all' in out
        assert 'DRIFT' not in out

    def test_zone_status_in_header(self):
        out = compare_markup(self.local, snap('edge.sg-labs.app', zone=False))
        assert 'not provisioned' in out
