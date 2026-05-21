# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: Schema__CF_TUI__Event_Row
# One parsed CF log line as the file viewer renders it — a compact, visual view of
# the fields that matter at a glance (time, method, status, uri, country, cache, bot,
# UA). Derived from Schema__CF__Event__Record by CF_TUI__File_Builder. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__CF_TUI__Event_Row(Type_Safe):
    time         : str                                                               # HH:MM:SS from the ISO timestamp
    method       : str
    status       : int = 0
    status_class : str                                                               # 2xx / 3xx / 4xx / 5xx / other
    uri          : str
    country      : str
    cache_hit    : bool = False
    is_bot       : bool = False
    user_agent   : str                                                               # truncated for the row
