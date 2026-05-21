# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: tests for the Screen-4 render (pure)
# Asserts the slug-detail sections — STATE + DNS real, instance/cost/activity pending
# — plus the not-found / no-slugs paths and the plain (no-markup) variant. No textual
# — runs on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State        import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Slug          import Schema__SG_Edge__TUI__Slug
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot      import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Slug_Detail__Render   import slug_detail_markup, slug_detail_plain

LIVE    = Enum__SG_Edge__TUI__Slug_State.LIVE
DORMANT = Enum__SG_Edge__TUI__Slug_State.DORMANT


def snap(slugs=(), parent='edge.sg-labs.local'):
    s = Schema__SG_Edge__TUI__Snapshot(parent=parent, captured_at=100, zone_exists=True, wildcard=True)
    for name, state in slugs:
        s.slugs.append(Schema__SG_Edge__TUI__Slug(slug=name, fqdn=f'{name}.{parent}', state=state,
                                                  backend_ip='127.0.0.1' if state == LIVE else '',
                                                  backend_port=8080 if state == LIVE else 0))
    return s


class test_slug_detail_render(TestCase):

    def test_live_slug__state_dns_real_rest_pending(self):
        out = slug_detail_markup(snap([('alice', LIVE), ('bob', DORMANT)]), 'alice')
        assert 'SLUG: alice'      in out
        assert '1 of 2'           in out                                             # position indicator
        assert 'STATE'            in out and 'live' in out
        assert 'alice.edge.sg-labs.local' in out                                     # fqdn / A record
        assert '127.0.0.1:8080'   in out                                            # real backend
        assert 'INSTANCE'         in out and 'pending Slice 5' in out                # honest pending
        assert 'ACTIVITY'         in out and 'pending observability' in out

    def test_dormant_slug__no_backend(self):
        out = slug_detail_markup(snap([('bob', DORMANT)]), 'bob')
        assert 'dormant' in out
        # dormant has A but no TXT → backend shows the em-dash placeholder
        assert 'TXT (backend) —' in out

    def test_not_found(self):
        out = slug_detail_markup(snap([('alice', LIVE)]), 'ghost')
        assert 'slug not found: ghost' in out

    def test_no_slugs(self):
        out = slug_detail_markup(snap([]), 'alice')
        assert 'no slugs registered' in out

    def test_plain__has_no_markup(self):
        out = slug_detail_plain(snap([('alice', LIVE)]), 'alice')
        assert '[bold]' not in out and '[green]' not in out and '[dim]' not in out
        assert 'SLUG: alice' in out
