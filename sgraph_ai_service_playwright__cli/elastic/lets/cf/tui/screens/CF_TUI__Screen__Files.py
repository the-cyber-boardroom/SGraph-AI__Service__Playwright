# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Screen__Files
# The S3 browser for CF log data. Two modes over the injected data source:
#   browse  — the .gz files for the scoped day/hour; ↑/↓ select, Enter opens
#   inspect — one file's parsed events (visual), `t` toggles raw TSV, Esc returns
# Thin view layer (framework carve-out from Type_Safe): all content is in the pure
# render module + the source seam; this class only wires Textual to them. Construct
# with an injected CF_TUI__Data_Source (tests pass an in-memory one — no mocks).
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app                                                                    import App, ComposeResult
from textual.containers                                                             import VerticalScroll
from textual.widgets                                                                import Header, Footer, Static

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Files__Render import files_browse_markup, file_view_markup
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__config            import TUI_REFRESH_SECONDS


class CF_TUI__Screen__Files(App):
    TITLE    = 'CF Log Files'
    BINDINGS = [('q',      'leave',       'Quit'),
                ('r',      'refresh',     'Refresh'),
                ('up',     'cursor_up',   'Up'),
                ('k',      'cursor_up',   'Up'),
                ('down',   'cursor_down', 'Down'),
                ('j',      'cursor_down', 'Down'),
                ('enter',  'open',        'Open'),
                ('escape', 'back',        'Back'),
                ('t',      'toggle_raw',  'Raw/parsed')]

    def __init__(self, source, date_iso : str = '', hour : str = '', max_files : int = 0,
                       refresh_seconds : float = TUI_REFRESH_SECONDS):
        super().__init__()
        self.source          = source
        self.date_iso        = date_iso
        self.hour            = hour
        self.max_files       = max_files
        self.refresh_seconds = refresh_seconds
        self.rows            = []
        self.selected        = 0
        self.mode            = 'browse'
        self.view            = None
        self.raw             = False
        self.exited          = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static('', id='body'))
        yield Footer()

    def on_mount(self) -> None:
        self.load_files()
        if self.refresh_seconds and self.refresh_seconds > 0:
            self.set_interval(self.refresh_seconds, self.poll)

    def poll(self) -> None:                                                          # only refresh the file list while browsing
        if self.mode == 'browse':
            self.load_files()

    def scope_label(self) -> str:
        scope = self.source.label()
        if self.date_iso:
            scope += f'  {self.date_iso}' + (f' {self.hour}h' if self.hour else '')
        return scope

    def load_files(self) -> None:
        self.rows = list(self.source.list_files(self.date_iso, self.hour, self.max_files))
        if self.selected >= len(self.rows):
            self.selected = max(0, len(self.rows) - 1)
        self.render_browse()

    def render_browse(self) -> None:
        self.mode = 'browse'
        self.query_one('#body', Static).update(files_browse_markup(self.rows, self.selected, self.scope_label()))

    def render_view(self) -> None:
        self.query_one('#body', Static).update(file_view_markup(self.view, self.raw))

    def action_cursor_down(self) -> None:
        if self.mode == 'browse' and self.rows:
            self.selected = min(self.selected + 1, len(self.rows) - 1)
            self.render_browse()

    def action_cursor_up(self) -> None:
        if self.mode == 'browse' and self.rows:
            self.selected = max(self.selected - 1, 0)
            self.render_browse()

    def action_open(self) -> None:
        if self.mode == 'browse' and self.rows:
            self.view = self.source.read_file(self.rows[self.selected].key)
            self.raw  = False
            self.mode = 'inspect'
            self.render_view()

    def action_back(self) -> None:
        if self.mode == 'inspect':
            self.render_browse()

    def action_toggle_raw(self) -> None:
        if self.mode == 'inspect' and self.view is not None:
            self.raw = not self.raw
            self.render_view()

    def action_refresh(self) -> None:
        if self.mode == 'browse':
            self.load_files()
        elif self.view is not None:
            self.view = self.source.read_file(self.view.key)
            self.render_view()

    def action_leave(self) -> None:
        self.exited = True
        self.exit()
