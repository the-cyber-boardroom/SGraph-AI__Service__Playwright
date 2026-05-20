# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: tests for the Screen-2 render (pure)
# Asserts the topology layers, slug rows, and the ▸ selection marker. No textual —
# runs on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State        import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Slug          import Schema__SG_Edge__TUI__Slug
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot      import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Topology__Render      import topology_markup

LIVE    = Enum__SG_Edge__TUI__Slug_State.LIVE
DORMANT = Enum__SG_Edge__TUI__Slug_State.DORMANT


def snap(slugs=(), fleet=(), wildcard=True, zone=True, parent='edge.sg-labs.local'):
    s = Schema__SG_Edge__TUI__Snapshot(parent=parent, captured_at=100, zone_exists=zone, wildcard=wildcard)
    for name, state in slugs:
        s.slugs.append(Schema__SG_Edge__TUI__Slug(slug=name, fqdn=f'{name}.{parent}', state=state,
                                                  backend_ip='127.0.0.1' if state == LIVE else '',
                                                  backend_port=8080 if state == LIVE else 0))
    for ip in fleet:
        s.fleet_ips.append(ip)
    return s


class test_topology_render(TestCase):

    def setUp(self):
        self.s = snap(slugs=[('alice', LIVE), ('bob', DORMANT)], fleet=['10.0.0.1'])

    def test_layers_and_slugs(self):
        out = topology_markup(self.s, selected_index=-1)
        for token in ('SG/Edge Topology', 'Browser', 'CloudFront / Wildcard',
                      'Edge Proxy fleet', '10.0.0.1', 'Vault backends', 'alice', 'bob', '▼'):
            assert token in out, token

    def test_selection_marker_moves(self):
        out0 = topology_markup(self.s, selected_index=0)
        out1 = topology_markup(self.s, selected_index=1)
        assert '▸' in out0 and '▸' in out1
        assert 'Selected:[/] alice' in out0                                          # detail line tracks the selection
        assert 'Selected:[/] bob'   in out1

    def test_not_provisioned(self):
        out = topology_markup(snap(zone=False))
        assert 'not provisioned' in out
        assert 'Edge Proxy fleet' not in out
