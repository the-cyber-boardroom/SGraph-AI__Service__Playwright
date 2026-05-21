# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: Schema__CF_TUI__Fixture_File
# A named blob of real CF TSV the in-memory source presents as a browsable "file"
# (key + tsv_text). Lets the file browser run with no AWS — and lets tests exercise
# multi-file browsing honestly (real log lines, just held in memory). Pure data.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__CF_TUI__Fixture_File(Type_Safe):
    key      : str
    tsv_text : str
