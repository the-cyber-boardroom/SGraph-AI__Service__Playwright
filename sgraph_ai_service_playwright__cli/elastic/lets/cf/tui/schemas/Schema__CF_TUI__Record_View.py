# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: Schema__CF_TUI__Record_View
# One CF log line walked through every field for the lineage inspector: the grouped
# Field_Rows (RAW → DERIVED → LINEAGE → PIPELINE), the doc_id, and the raw line.
# `valid` is False when the line did not have 26 TSV columns (the parser's contract).
# Built by CF_TUI__Record_Builder. Pure data — no methods.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.List__CF_TUI__Field_Row import List__CF_TUI__Field_Row


class Schema__CF_TUI__Record_View(Type_Safe):
    key          : str
    line_index   : int  = 0
    doc_id       : str
    valid        : bool = False
    column_count : int  = 0                                                          # raw TSV column count (26 expected) — diagnostics on invalid
    fields       : List__CF_TUI__Field_Row
    raw_line     : str
