# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: List__SG_Edge__TUI__Event
# Typed list of Schema__SG_Edge__TUI__Event. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List import Type_Safe__List

from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Event  import Schema__SG_Edge__TUI__Event


class List__SG_Edge__TUI__Event(Type_Safe__List):
    expected_type = Schema__SG_Edge__TUI__Event
