# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Table
# Generic Type_Safe → table-rows helper for Textual DataTable. Introspects each
# schema via .json() to derive columns/values, so ANY Type_Safe list becomes a table
# with no per-schema code. Pure (no textual) → testable on 3.11.
#
# NOTE: osbot-fast-api ships a richer Type_Safe→table converter (used for its HTML
# admin tables). This is a deliberately tiny local stand-in for the DataTable
# prototype; consolidate with the Fast_API class if/when the DataTable approach is
# promoted (it is not installed in this container, so it could not be reused here).
# ═══════════════════════════════════════════════════════════════════════════════


def type_safe_table(items, columns=None) -> tuple:
    materialised = list(items)
    if not materialised:
        return (list(columns) if columns else []), []
    first = materialised[0].json()
    cols  = list(columns) if columns else list(first.keys())
    rows  = []
    for item in materialised:
        data = item.json()
        rows.append([_cell(data.get(col)) for col in cols])
    return cols, rows


def _cell(value) -> str:
    return '' if value is None else str(value)
