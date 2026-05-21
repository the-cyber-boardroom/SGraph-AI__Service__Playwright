# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui components: Tui__App
# The reusable base for every sg aws TUI screen. It owns the chrome so screens don't
# repeat it: Header, a scrollable main body, the collapsible Debug Panel on the right
# (open by default, `d` toggles), and Footer — plus the shared Debug__Event_Log that
# the screen's source/service writes to. Subclasses implement populate() to render the
# body (set_body markup) and may extend BINDINGS; refresh (r) re-runs populate. This
# is the "component-first" backbone: a new screen is "subclass Tui__App, implement
# populate()", and the debug feed comes for free.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app        import App, ComposeResult
from textual.binding    import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets    import Header, Footer, Static

from sgraph_ai_service_playwright__cli.tui.components.Debug__Panel import Debug__Panel
from sgraph_ai_service_playwright__cli.tui.debug.Debug__Event_Log  import Debug__Event_Log

CSS_BASE = """
#tui-main { width: 1fr; padding: 0 1; }
"""


class Tui__App(App):
    CSS      = CSS_BASE
    BINDINGS = [Binding('d', 'toggle_debug', 'Debug'),
                Binding('r', 'refresh',      'Refresh'),
                Binding('q', 'leave',        'Quit')]

    def __init__(self, debug_log=None, debug_open : bool = True, refresh_seconds : float = 0.0, **kwargs):
        super().__init__(**kwargs)
        self.debug_log       = debug_log if debug_log is not None else Debug__Event_Log()
        self.debug_open      = debug_open
        self.refresh_seconds = refresh_seconds
        self.exited          = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield VerticalScroll(Static('', id='body'), id='tui-main')
            yield Debug__Panel(self.debug_log, id='debug-panel')
        yield Footer()

    def on_mount(self) -> None:
        self.apply_debug_visibility()
        self.populate()
        self.refresh_debug()
        if self.refresh_seconds and self.refresh_seconds > 0:
            self.set_interval(self.refresh_seconds, self.tick)

    def tick(self) -> None:
        self.populate()
        self.refresh_debug()

    # ── subclass hook ───────────────────────────────────────────────────────────
    def populate(self) -> None:                                                      # render the body; default no-op
        pass

    # ── shared helpers ──────────────────────────────────────────────────────────
    def set_body(self, markup : str) -> None:
        self.query_one('#body', Static).update(markup)

    def refresh_debug(self) -> None:
        self.query_one('#debug-panel', Debug__Panel).refresh_log()

    def log_event(self, category : str, message : str, detail : str = '', ok : bool = True) -> None:
        self.debug_log.record(category, message, detail, ok)
        self.refresh_debug()

    def apply_debug_visibility(self) -> None:
        self.query_one('#debug-panel', Debug__Panel).set_class(not self.debug_open, '-hidden')

    # ── actions ─────────────────────────────────────────────────────────────────
    def action_toggle_debug(self) -> None:
        self.debug_open = not self.debug_open
        self.apply_debug_visibility()

    def action_refresh(self) -> None:
        self.populate()
        self.refresh_debug()

    def action_leave(self) -> None:
        self.exited = True
        self.exit()
