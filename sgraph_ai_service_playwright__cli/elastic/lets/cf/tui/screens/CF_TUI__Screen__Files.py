# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Screen__Files
# The S3 browser for CF log data. Three levels over the injected data source:
#   dir    — folders + files at the current prefix; ↑/↓ select, Enter descends/opens,
#            Esc goes up a level (walks the YYYY/MM/DD/HH partitions)
#   file   — one object's parsed events; ↑/↓ select a row, Enter inspects its fields,
#            `t` toggles raw TSV, Esc returns to the folder
#   record — the Field Lineage Inspector for one event; Esc returns to the file
# Thin view layer (framework carve-out): all content is pure render + source seam;
# this class only wires Textual to them. Construct with an injected data source.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app                                                                    import App, ComposeResult
from textual.containers                                                             import VerticalScroll
from textual.widgets                                                                import Header, Footer, Static

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Files__Render     import dir_browse_markup, file_view_markup
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Inspector__Render import inspector_markup
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

    def __init__(self, source, start_prefix : str = '', refresh_seconds : float = TUI_REFRESH_SECONDS):
        super().__init__()
        self.source          = source
        self.prefix          = start_prefix
        self.refresh_seconds = refresh_seconds
        self.stack           = []                                                    # prefixes to pop on Esc (folder "up")
        self.entries         = []
        self.selected        = 0
        self.mode            = 'dir'
        self.view            = None                                                  # current File_View
        self.event_selected  = 0
        self.record          = None                                                  # current Record_View
        self.raw             = False
        self.exited          = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static('', id='body'))
        yield Footer()

    def on_mount(self) -> None:
        self.load_dir()
        if self.refresh_seconds and self.refresh_seconds > 0:
            self.set_interval(self.refresh_seconds, self.poll)

    def poll(self) -> None:
        if self.mode == 'dir':
            self.load_dir()

    def body(self) -> Static:
        return self.query_one('#body', Static)

    # ─── dir level ───────────────────────────────────────────────────────────
    def load_dir(self) -> None:
        self.entries = list(self.source.list_dir(self.prefix))
        if self.selected >= len(self.entries):
            self.selected = max(0, len(self.entries) - 1)
        self.render_dir()

    def render_dir(self) -> None:
        self.mode = 'dir'
        self.body().update(dir_browse_markup(self.entries, self.selected, self.prefix, self.source.label()))

    # ─── file level ──────────────────────────────────────────────────────────
    def render_file(self) -> None:
        self.body().update(file_view_markup(self.view, self.raw, self.event_selected))

    # ─── record level ────────────────────────────────────────────────────────
    def render_record(self) -> None:
        self.body().update(inspector_markup(self.record))

    # ─── actions ───────────────────────────────────────────────────────────────
    def action_cursor_down(self) -> None:
        if self.mode == 'dir' and self.entries:
            self.selected = min(self.selected + 1, len(self.entries) - 1)
            self.render_dir()
        elif self.mode == 'file' and self.view and self.view.events:
            self.event_selected = min(self.event_selected + 1, len(self.view.events) - 1)
            self.render_file()

    def action_cursor_up(self) -> None:
        if self.mode == 'dir' and self.entries:
            self.selected = max(self.selected - 1, 0)
            self.render_dir()
        elif self.mode == 'file' and self.view and self.view.events:
            self.event_selected = max(self.event_selected - 1, 0)
            self.render_file()

    def action_open(self) -> None:
        if self.mode == 'dir' and self.entries:
            entry = self.entries[self.selected]
            if entry.is_folder:
                self.stack.append(self.prefix)
                self.prefix   = entry.path
                self.selected = 0
                self.load_dir()
            else:
                self.view           = self.source.read_file(entry.path)
                self.event_selected = 0
                self.raw            = False
                self.mode           = 'file'
                self.render_file()
        elif self.mode == 'file' and self.view and self.view.events:
            self.record = self.source.read_record(self.view.key, self.event_selected)
            self.mode   = 'record'
            self.render_record()

    def action_back(self) -> None:
        if self.mode == 'record':
            self.mode = 'file'
            self.render_file()
        elif self.mode == 'file':
            self.load_dir()
        elif self.mode == 'dir' and self.stack:
            self.prefix   = self.stack.pop()
            self.selected = 0
            self.load_dir()

    def action_toggle_raw(self) -> None:
        if self.mode == 'file' and self.view is not None:
            self.raw = not self.raw
            self.render_file()

    def action_refresh(self) -> None:
        if   self.mode == 'dir'                          : self.load_dir()
        elif self.mode == 'file' and self.view is not None:
            self.view = self.source.read_file(self.view.key)
            self.render_file()
        elif self.mode == 'record' and self.record is not None:
            self.record = self.source.read_record(self.record.key, self.record.line_index)
            self.render_record()

    def action_leave(self) -> None:
        self.exited = True
        self.exit()
