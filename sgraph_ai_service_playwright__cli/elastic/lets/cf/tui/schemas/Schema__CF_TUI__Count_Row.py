# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: Schema__CF_TUI__Count_Row
# One labelled tally for a top-N panel (top URI, top bot UA, country, status class).
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__CF_TUI__Count_Row(Type_Safe):
    label : str
    count : int = 0
