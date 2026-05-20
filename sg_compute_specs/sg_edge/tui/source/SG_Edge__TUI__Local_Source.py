# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Local_Source
# Data source over the file-backed local edge. snapshot() builds from a helper over
# the local DNS (so it renders identically to the AWS source); the deployed flag is
# the local stack marker. Mutations delegate to Local__Edge__Stack — reusing its
# tested setup/register/unregister/request/teardown rather than reimplementing them.
# Tests inject a stack pointed at a temp state dir (no AWS, no mocks).
# ═══════════════════════════════════════════════════════════════════════════════

from sg_compute_specs.sg_edge.service.SG_Edge__DNS__Helper                          import SG_Edge__DNS__Helper
from sg_compute_specs.sg_edge.local.Local__Edge__Stack                              import Local__Edge__Stack
from sg_compute_specs.sg_edge.local.Local__Route53__Client                          import Local__Route53__Client
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Target                  import Enum__SG_Edge__TUI__Target
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot            import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.service.SG_Edge__TUI__Snapshot__Builder           import SG_Edge__TUI__Snapshot__Builder
from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__Data_Source                  import SG_Edge__TUI__Data_Source


class SG_Edge__TUI__Local_Source(SG_Edge__TUI__Data_Source):
    stack   : Local__Edge__Stack
    builder : SG_Edge__TUI__Snapshot__Builder

    def target(self) -> Enum__SG_Edge__TUI__Target:
        return Enum__SG_Edge__TUI__Target.LOCAL

    def parent(self) -> str:
        return self.stack.parent

    def helper(self) -> SG_Edge__DNS__Helper:                                        # fresh client per call → reads the on-disk DNS the prior process wrote
        return SG_Edge__DNS__Helper(route53=Local__Route53__Client(dns_path=self.stack.dns_path()))

    def snapshot(self) -> Schema__SG_Edge__TUI__Snapshot:
        return self.builder.build(self.helper(), self.target(), self.stack.parent, deployed=self.stack.is_deployed())

    def can_act(self) -> bool:
        return True

    def setup(self):
        return self.stack.setup()

    def register(self, slug : str, with_backend : bool = True):
        return self.stack.register(slug, with_backend=with_backend)

    def unregister(self, slug : str):
        return self.stack.unregister(slug)

    def request(self, slug : str):
        return self.stack.request(slug)

    def teardown(self):
        return self.stack.teardown()
