# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — s3 tui: S3_Browser__Screen
# A generic S3 bucket / folder / file browser + viewer. Three levels over the
# injected source:
#   buckets — every bucket; Enter opens one
#   dir     — folders + files at a prefix; ↑/↓ select, Enter descends/opens, Esc up
#   object  — one object's decoded preview; Esc returns
# Thin view layer (framework carve-out): content is pure render + source seam; this
# class only wires Textual to them. Construct with an injected S3_Browser__Source.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app                                                                  import App, ComposeResult
from textual.containers                                                           import VerticalScroll
from textual.widgets                                                              import Header, Footer, Static

from sgraph_ai_service_playwright__cli.aws.s3.tui.screens.S3_Browser__Render       import entries_markup, object_markup


class S3_Browser__Screen(App):
    TITLE    = 'S3 Browser'
    BINDINGS = [('q',      'leave',       'Quit'),
                ('r',      'refresh',     'Refresh'),
                ('up',     'cursor_up',   'Up'),
                ('k',      'cursor_up',   'Up'),
                ('down',   'cursor_down', 'Down'),
                ('j',      'cursor_down', 'Down'),
                ('enter',  'open',        'Open'),
                ('escape', 'back',        'Back')]

    def __init__(self, source, start_bucket : str = '', start_prefix : str = '', refresh_seconds : float = 0.0):
        super().__init__()
        self.source          = source
        self.bucket          = start_bucket
        self.prefix          = start_prefix
        self.start_bucket    = start_bucket
        self.refresh_seconds = refresh_seconds
        self.stack           = []                                                   # prefixes to pop on Esc within a bucket
        self.entries         = []
        self.selected        = 0
        self.mode            = 'buckets'
        self.view            = None
        self.exited          = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(Static('', id='body'))
        yield Footer()

    def on_mount(self) -> None:
        if self.start_bucket:
            self.load_dir(self.start_bucket, self.prefix)
        else:
            self.load_buckets()

    def body(self) -> Static:
        return self.query_one('#body', Static)

    def load_buckets(self) -> None:
        self.mode     = 'buckets'
        self.entries  = list(self.source.list_buckets())
        self.selected = min(self.selected, max(0, len(self.entries) - 1))
        self.body().update(entries_markup(self.entries, self.selected, 's3://'))

    def load_dir(self, bucket : str, prefix : str) -> None:
        self.mode     = 'dir'
        self.bucket   = bucket
        self.prefix   = prefix
        self.entries  = list(self.source.list_dir(bucket, prefix))
        if self.selected >= len(self.entries):
            self.selected = max(0, len(self.entries) - 1)
        self.body().update(entries_markup(self.entries, self.selected, f's3://{bucket}/{prefix}'))

    def render_object(self) -> None:
        self.body().update(object_markup(self.view))

    def action_cursor_down(self) -> None:
        if self.mode in ('buckets', 'dir') and self.entries:
            self.selected = min(self.selected + 1, len(self.entries) - 1)
            self._rerender_list()

    def action_cursor_up(self) -> None:
        if self.mode in ('buckets', 'dir') and self.entries:
            self.selected = max(self.selected - 1, 0)
            self._rerender_list()

    def _rerender_list(self) -> None:
        if self.mode == 'buckets':
            self.body().update(entries_markup(self.entries, self.selected, 's3://'))
        else:
            self.body().update(entries_markup(self.entries, self.selected, f's3://{self.bucket}/{self.prefix}'))

    def action_open(self) -> None:
        if not self.entries:
            return
        entry = self.entries[self.selected]
        if self.mode == 'buckets':
            self.selected = 0
            self.stack    = []
            self.load_dir(entry.bucket, '')
        elif self.mode == 'dir':
            if entry.kind == 'folder':
                self.stack.append(self.prefix)
                self.selected = 0
                self.load_dir(self.bucket, entry.path)
            else:
                self.view = self.source.read_object(self.bucket, entry.path)
                self.mode = 'object'
                self.render_object()

    def action_back(self) -> None:
        if self.mode == 'object':
            self.load_dir(self.bucket, self.prefix)
        elif self.mode == 'dir':
            if self.stack:
                self.selected = 0
                self.load_dir(self.bucket, self.stack.pop())
            elif not self.start_bucket:                                             # at bucket root → back to bucket list
                self.selected = 0
                self.load_buckets()

    def action_refresh(self) -> None:
        if   self.mode == 'buckets'                  : self.load_buckets()
        elif self.mode == 'dir'                      : self.load_dir(self.bucket, self.prefix)
        elif self.mode == 'object' and self.view is not None:
            self.view = self.source.read_object(self.view.bucket, self.view.key)
            self.render_object()

    def action_leave(self) -> None:
        self.exited = True
        self.exit()
