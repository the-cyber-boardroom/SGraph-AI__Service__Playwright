# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: Schema__CF_TUI__Dir_Entry
# One row in the folder browser: either a child folder (is_folder=True, path is the
# child prefix) or a file (is_folder=False, path is the full object key). Lets the
# browser walk the cloudfront-realtime/{YYYY}/{MM}/{DD}/{HH}/ partitions. Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__CF_TUI__Dir_Entry(Type_Safe):
    name         : str                                                               # display name (folder segment or file basename)
    is_folder    : bool = False
    path         : str                                                               # child prefix (folder) or full key (file)
    size_bytes   : int  = 0                                                          # files only
    delivery_iso : str                                                              # files only — Firehose timestamp from the filename
