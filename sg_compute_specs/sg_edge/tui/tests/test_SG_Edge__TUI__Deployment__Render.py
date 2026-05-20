# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: tests for the Screen-1 render (pure) + glyphs
# Asserts the Deployment Reality markup string and the shared glyph helpers. No
# textual, no rich — runs on 3.11 (the content is decoupled from the view layer).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.sg_edge.local.enums.Enum__Local__Edge__Severity        import Enum__Local__Edge__Severity
from sg_compute_specs.sg_edge.local.schemas.Schema__Local__Edge__Issue       import Schema__Local__Edge__Issue
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State        import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Slug          import Schema__SG_Edge__TUI__Slug
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot      import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Deployment__Render    import deployment_markup
from sg_compute_specs.sg_edge.tui.screens.widgets.SG_Edge__TUI__Glyphs        import slug_glyph, severity_glyph, yes_no

LIVE    = Enum__SG_Edge__TUI__Slug_State.LIVE
DORMANT = Enum__SG_Edge__TUI__Slug_State.DORMANT


def snap(slugs=(), fleet=(), issues=(), zone=True, wildcard=True, parent='edge.sg-labs.local'):
    s = Schema__SG_Edge__TUI__Snapshot(parent=parent, captured_at=100, zone_exists=zone, wildcard=wildcard)
    for name, state in slugs:
        s.slugs.append(Schema__SG_Edge__TUI__Slug(slug=name, fqdn=f'{name}.{parent}', state=state,
                                                  backend_ip='127.0.0.1' if state == LIVE else '',
                                                  backend_port=8080 if state == LIVE else 0))
    for ip in fleet:
        s.fleet_ips.append(ip)
    for area, message in issues:
        s.issues.append(Schema__Local__Edge__Issue(area=area, message=message))
    return s


class test_SG_Edge__TUI__Glyphs(TestCase):

    def test_slug_glyph(self):
        assert slug_glyph(LIVE)    == ('●', 'green')
        assert slug_glyph(DORMANT) == ('◐', 'yellow')

    def test_severity_glyph(self):
        assert severity_glyph(Enum__Local__Edge__Severity.WARN)  == ('⚠', 'yellow')
        assert severity_glyph(Enum__Local__Edge__Severity.ERROR) == ('✗', 'red')

    def test_yes_no(self):
        assert yes_no(True)  == ('✓', 'green')
        assert yes_no(False) == ('✗', 'red')


class test_deployment_markup(TestCase):

    def test_provisioned__sections_slugs_and_pending(self):
        out = deployment_markup(snap(slugs=[('alice', LIVE), ('bob', DORMANT)],
                                     fleet=['10.0.0.1'],
                                     issues=[('slug:bob', 'registered but dormant')]))
        for token in ('Deployment Reality', 'EDGE INFRASTRUCTURE', 'PROXY FLEET',
                      'REGISTERED SLUGS', 'alice', 'bob', '10.0.0.1', 'CHECKS'):
            assert token in out, token
        assert 'pending Slice 5' in out                                              # honesty: instance/vault panes named, not faked
        assert '127.0.0.1:8080'  in out                                              # live backend shown

    def test_not_provisioned(self):
        out = deployment_markup(snap(zone=False))
        assert 'not provisioned' in out
        assert 'EDGE INFRASTRUCTURE' not in out
