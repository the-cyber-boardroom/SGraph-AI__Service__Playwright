# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: Schema__CF_TUI__Traffic_Snapshot
# The one normalised, source-independent snapshot the Traffic Reality screen renders.
# Produced by CF_TUI__Aggregator from real parsed CF events (in-memory fixtures or
# the live S3 bucket). Every tally traces to parsed records — nothing is fabricated;
# when no events are available the panels render zeros, not invented numbers.
# Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.enums.Enum__CF_TUI__Source        import Enum__CF_TUI__Source
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.List__CF_TUI__Count_Row   import List__CF_TUI__Count_Row
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.List__CF_TUI__Series_Point import List__CF_TUI__Series_Point


class Schema__CF_TUI__Traffic_Snapshot(Type_Safe):
    source         : Enum__CF_TUI__Source = Enum__CF_TUI__Source.IN_MEMORY            # which source produced it
    source_label   : str                                                             # human label shown on screen (e.g. "in-memory (fixtures)" / bucket/prefix)
    captured_at    : int = 0                                                          # unix seconds the snapshot was taken
    files_sampled  : int = 0                                                          # .gz objects (or fixture blobs) read for this snapshot
    lines_skipped  : int = 0                                                          # rows the parser could not decode (honest error surface)
    total_events   : int = 0
    bot_events     : int = 0                                                          # bot_category in {BOT_KNOWN, BOT_GENERIC}
    human_events   : int = 0                                                          # bot_category == HUMAN
    unknown_events : int = 0                                                          # bot_category == UNKNOWN (empty UA)
    cache_hits     : int = 0
    cache_other    : int = 0                                                          # everything that is not a cache hit (miss / error / generated)
    top_uris       : List__CF_TUI__Count_Row                                          # most-requested cs_uri_stem values
    status_classes : List__CF_TUI__Count_Row                                          # 2xx / 3xx / 4xx / 5xx tallies
    top_countries  : List__CF_TUI__Count_Row                                          # c_country tallies
    top_bots       : List__CF_TUI__Count_Row                                          # truncated bot user-agents (is_bot rows only)
    throughput     : List__CF_TUI__Series_Point                                       # events per minute bucket (sparkline)
