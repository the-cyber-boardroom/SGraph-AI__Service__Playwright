# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: Schema__SG_Edge__TUI__Comparison_Row
# One row of the local-vs-edge comparison (Screen 3): a named component and whether
# it is present on each side, with the resulting sync verdict. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                       import Type_Safe

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Sync_State      import Enum__SG_Edge__TUI__Sync_State


class Schema__SG_Edge__TUI__Comparison_Row(Type_Safe):
    name          : str
    local_present : bool = False
    edge_present  : bool = False
    sync_state    : Enum__SG_Edge__TUI__Sync_State = Enum__SG_Edge__TUI__Sync_State.IN_SYNC
