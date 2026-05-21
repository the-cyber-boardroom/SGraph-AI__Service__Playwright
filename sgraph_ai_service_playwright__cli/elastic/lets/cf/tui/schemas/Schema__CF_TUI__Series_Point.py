# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: Schema__CF_TUI__Series_Point
# One bucket of a throughput series (label = the minute bucket "HH:MM", value =
# event count). Drives the throughput sparkline honestly — every point is a real
# count of parsed events in that bucket. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__CF_TUI__Series_Point(Type_Safe):
    label : str
    value : int = 0
