# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: List__SG_Edge__TUI__Capability
# Typed list of Enum__SG_Edge__TUI__Capability — which panes a snapshot can back
# with real data. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Capability import Enum__SG_Edge__TUI__Capability


class List__SG_Edge__TUI__Capability(Type_Safe__List):
    expected_type = Enum__SG_Edge__TUI__Capability
