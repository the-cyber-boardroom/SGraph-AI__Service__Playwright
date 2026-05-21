# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf local: Schema__CF__Local__Stats
# What the local raw-cf-logs cache holds: totals, partition coverage, and a per-day
# breakdown. Drives the cache-stats screen (and the later "is today complete?"
# question). Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                              import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.List__CF__Local__Day_Stat import List__CF__Local__Day_Stat


class Schema__CF__Local__Stats(Type_Safe):
    data_type   : str
    base_path   : str
    exists      : bool = False
    total_files : int  = 0
    total_bytes : int  = 0
    day_count   : int  = 0
    hour_count  : int  = 0
    first_day   : str
    last_day    : str
    days        : List__CF__Local__Day_Stat
