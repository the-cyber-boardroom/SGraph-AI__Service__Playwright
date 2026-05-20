# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__AWS_Source
# Read-only data source over the live AWS edge DNS (edge.sg-labs.app). It reads the
# real registry — proxies.<parent> A, _state TXT, _sg.<slug> TXT — so the topology /
# slugs / fleet / checks panes show genuine edge state today. Cost/throughput/
# instance panes carry no data yet (absent from capabilities). Mutations are NOT
# wired until v0.2.37 Slice 5, so can_act() is False and the action methods raise —
# screens disable the keys rather than calling them. Tests inject a
# Route53__AWS__Client__In_Memory into the helper (no mocks).
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper                          import SG_Edge__DNS__Helper
from sg_compute_specs.sg_edge.local.sg_edge_local__config                           import SG_EDGE__AWS_PARENT
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Target                  import Enum__SG_Edge__TUI__Target
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot            import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.service.SG_Edge__TUI__Snapshot__Builder           import SG_Edge__TUI__Snapshot__Builder
from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__Data_Source                  import SG_Edge__TUI__Data_Source

SLICE_5 = 'AWS edge mutations are not wired yet — pending v0.2.37 Slice 5 (live EC2)'


class SG_Edge__TUI__AWS_Source(SG_Edge__TUI__Data_Source):
    dns         : SG_Edge__DNS__Helper                                               # inject route53 (real client, or in-memory for tests)
    builder     : SG_Edge__TUI__Snapshot__Builder
    parent_zone : str = SG_EDGE__AWS_PARENT

    def target(self) -> Enum__SG_Edge__TUI__Target:
        return Enum__SG_Edge__TUI__Target.AWS

    def parent(self) -> str:
        return self.parent_zone

    def snapshot(self) -> Schema__SG_Edge__TUI__Snapshot:                            # deployed=None → derived from zone presence
        return self.builder.build(self.dns, self.target(), self.parent_zone)

    def can_act(self) -> bool:
        return False

    def setup(self):
        raise NotImplementedError(SLICE_5)

    def register(self, slug : str, with_backend : bool = True):
        raise NotImplementedError(SLICE_5)

    def unregister(self, slug : str):
        raise NotImplementedError(SLICE_5)

    def request(self, slug : str):
        raise NotImplementedError(SLICE_5)

    def teardown(self):
        raise NotImplementedError(SLICE_5)
