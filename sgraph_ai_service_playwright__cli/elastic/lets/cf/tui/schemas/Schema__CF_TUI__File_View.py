# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: Schema__CF_TUI__File_View
# One CF-logs object opened in the file browser: the parsed event rows (visual view)
# plus the raw gunzipped TSV (raw view, `t` toggle) and the counts. Built by
# CF_TUI__File_Builder from the object's bytes. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.List__CF_TUI__Event_Row import List__CF_TUI__Event_Row


class Schema__CF_TUI__File_View(Type_Safe):
    key           : str
    size_bytes    : int = 0
    total_events  : int = 0
    lines_skipped : int = 0
    events        : List__CF_TUI__Event_Row                                          # parsed, compact, for the visual view
    raw_text      : str                                                              # gunzipped TSV (capped) for the raw view
