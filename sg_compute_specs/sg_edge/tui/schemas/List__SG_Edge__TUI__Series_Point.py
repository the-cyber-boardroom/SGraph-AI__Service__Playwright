# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: List__SG_Edge__TUI__Series_Point
# Typed list of Schema__SG_Edge__TUI__Series_Point. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List         import Type_Safe__List

from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Series_Point   import Schema__SG_Edge__TUI__Series_Point


class List__SG_Edge__TUI__Series_Point(Type_Safe__List):
    expected_type = Schema__SG_Edge__TUI__Series_Point
