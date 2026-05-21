# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Screen__Sync
# The "sync raw-cf-logs" screen. Subclasses the shared Tui__App, so the Debug Panel
# (showing every S3 list/get + local write) and the chrome come for free — it only
# implements populate() and a `g` action. The download runs in a Textual thread worker
# (leverage textual) so the UI and debug feed update live per file; the screen shares
# the sync service's Debug__Event_Log with the panel. Construct with a CF__Logs__Sync.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.binding import Binding

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Sync__Render import sync_markup
from sgraph_ai_service_playwright__cli.tui.components.Tui__App                    import Tui__App


class CF_TUI__Screen__Sync(Tui__App):
    TITLE    = 'Sync · raw-cf-logs'
    BINDINGS = [Binding('g', 'download', 'Download missing')]

    def __init__(self, sync, date_iso : str = '', hour : str = '', **kwargs):
        super().__init__(debug_log=sync.debug, **kwargs)
        self.sync     = sync
        self.date_iso = date_iso
        self.hour     = hour
        self.plan     = None
        self.result   = None
        self.busy     = False

    def populate(self) -> None:
        if self.plan is None:
            self.plan = self.sync.plan(self.date_iso, self.hour)
        self.set_body(sync_markup(self.plan, self.result, self.busy))

    def action_refresh(self) -> None:                                                # re-list S3 (cheap; immutable means only "is today complete?" changes)
        self.plan   = self.sync.plan(self.date_iso, self.hour)
        self.result = None
        self.set_body(sync_markup(self.plan, self.result, self.busy))
        self.refresh_debug()

    def action_download(self) -> None:
        if self.busy or self.plan is None or self.plan.missing_count == 0:
            return
        self.busy   = True
        self.result = None
        self.set_body(sync_markup(self.plan, self.result, True))
        self.refresh_debug()
        self.run_worker(self.download_worker, thread=True, exclusive=True)

    def download_worker(self) -> None:                                               # runs off the UI thread
        def on_file(result, _f):
            self.call_from_thread(self.on_progress, result)
        result = self.sync.download_missing(self.plan, on_file=on_file)
        self.call_from_thread(self.on_done, result)

    def on_progress(self, result) -> None:
        self.result = result
        self.set_body(sync_markup(self.plan, self.result, True))
        self.refresh_debug()

    def on_done(self, result) -> None:
        self.result = result
        self.busy   = False
        self.plan   = self.sync.plan(self.date_iso, self.hour)                       # re-plan: now-present files flip to ✓
        self.set_body(sync_markup(self.plan, self.result, False))
        self.refresh_debug()
