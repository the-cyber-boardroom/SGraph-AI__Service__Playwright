# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Screen__Slugs  (DataTable PROTOTYPE)
# A slug inventory rendered with Textual's DataTable widget instead of a markup
# Static — the comparison piece for the "leverage Textual more" review. DataTable
# gives, for free, what the markup screens hand-roll: a row cursor (↑/↓), scrolling,
# zebra striping, mouse selection, and a RowSelected event (Enter/click → drill).
# Rows come from the generic Type_Safe→table helper (any schema list works).
#
# Construct with an injected source. Enter/click a row → records opened_slug + exits
# (the CLI relaunches Slug detail), mirroring the Topology drill-in.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app                                                                    import ComposeResult
from textual.widgets                                                                import Header, Footer, DataTable

from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__App__Base                   import SG_Edge__TUI__App__Base
from sg_compute_specs.sg_edge.tui.screens.widgets.SG_Edge__TUI__Table               import type_safe_table
from sg_compute_specs.sg_edge.tui.sg_edge_tui__config                               import TUI_REFRESH_SECONDS

SLUG_COLUMNS = ['slug', 'state', 'backend_ip', 'backend_port', 'fqdn']               # Schema__SG_Edge__TUI__Slug fields


class SG_Edge__TUI__Screen__Slugs(SG_Edge__TUI__App__Base):
    TITLE    = 'SG/Edge Slugs'
    BINDINGS = [('r', 'refresh', 'Refresh')]                                         # ↑/↓ + Enter are DataTable built-ins

    def __init__(self, source, refresh_seconds : float = TUI_REFRESH_SECONDS):
        super().__init__()
        self.source          = source
        self.refresh_seconds = refresh_seconds
        self.snapshot        = None
        self.opened_slug     = ''

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id='slugs', cursor_type='row', zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one('#slugs', DataTable)
        table.add_columns('slug', 'state', 'backend ip', 'backend port', 'fqdn')
        self.refresh_rows()
        table.focus()                                                                # so ↑/↓ route to the table
        if self.refresh_seconds and self.refresh_seconds > 0:
            self.set_interval(self.refresh_seconds, self.refresh_rows)

    def card_snapshot(self):
        return self.snapshot

    def refresh_rows(self) -> None:
        self.snapshot = self.source.snapshot()
        table         = self.query_one('#slugs', DataTable)
        cursor        = table.cursor_row
        table.clear()
        _, rows = type_safe_table(self.snapshot.slugs, SLUG_COLUMNS)
        for row in rows:
            table.add_row(*row)
        if table.row_count:
            table.move_cursor(row=min(cursor, table.row_count - 1))                  # keep the cursor put across refreshes

    def action_refresh(self) -> None:
        self.refresh_rows()

    def selected_slug(self) -> str:
        slugs = self.snapshot.slugs if self.snapshot else []
        index = self.query_one('#slugs', DataTable).cursor_row
        return slugs[index].slug if 0 <= index < len(slugs) else ''

    def on_data_table_row_selected(self, event) -> None:                             # Enter or mouse click on a row
        slug = self.selected_slug()
        if slug:
            self.opened_slug = slug
            self.exit()
