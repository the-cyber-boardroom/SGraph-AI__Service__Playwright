# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Data_Source
# The seam every screen reads through. snapshot() returns the one normalised
# Schema__SG_Edge__TUI__Snapshot; the action methods mutate the edge. can_act()
# tells a screen whether to enable action keys — the AWS source returns False until
# Slice 5 wires live mutations, so the screen shows a disabled hint, not an error.
#
# Base class — concrete sources (Local / AWS) override. Kept thin: this is the
# subscription-to-primitive-output the plan calls for, with no parallel state.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                       import Type_Safe

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Target          import Enum__SG_Edge__TUI__Target
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot    import Schema__SG_Edge__TUI__Snapshot


class SG_Edge__TUI__Data_Source(Type_Safe):

    def target(self) -> Enum__SG_Edge__TUI__Target:
        raise NotImplementedError

    def parent(self) -> str:
        raise NotImplementedError

    def snapshot(self) -> Schema__SG_Edge__TUI__Snapshot:
        raise NotImplementedError

    def can_act(self) -> bool:                                                       # may the screen enable mutating actions?
        return False

    def setup(self):
        raise NotImplementedError

    def register(self, slug : str, with_backend : bool = True):
        raise NotImplementedError

    def unregister(self, slug : str):
        raise NotImplementedError

    def request(self, slug : str):
        raise NotImplementedError

    def teardown(self):
        raise NotImplementedError
