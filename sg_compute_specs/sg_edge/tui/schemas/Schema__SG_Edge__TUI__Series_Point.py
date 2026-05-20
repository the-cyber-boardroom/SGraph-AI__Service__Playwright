# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: Schema__SG_Edge__TUI__Series_Point
# One (timestamp, value) point in a sparkline series. The TUI measures these itself
# from successive snapshots — honest time-series, not synthetic rps. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__SG_Edge__TUI__Series_Point(Type_Safe):
    ts    : int = 0
    value : int = 0
