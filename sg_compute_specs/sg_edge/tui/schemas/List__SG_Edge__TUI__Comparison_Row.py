# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: List__SG_Edge__TUI__Comparison_Row
# Typed list of Schema__SG_Edge__TUI__Comparison_Row. Pure type definition — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.type_safe_core.collections.Type_Safe__List          import Type_Safe__List

from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Comparison_Row  import Schema__SG_Edge__TUI__Comparison_Row


class List__SG_Edge__TUI__Comparison_Row(Type_Safe__List):
    expected_type = Schema__SG_Edge__TUI__Comparison_Row
