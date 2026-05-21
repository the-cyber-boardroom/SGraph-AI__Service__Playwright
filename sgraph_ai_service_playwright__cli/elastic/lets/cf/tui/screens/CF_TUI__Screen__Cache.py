# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Screen__Cache
# Local raw-cf-logs cache stats. Subclasses the shared Tui__App, so the Debug Panel
# and chrome come for free; populate() walks the store and records the scan to the
# debug feed so the panel shows the fs read. Construct with a CF__Local__Store.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Cache__Render import cache_stats_markup
from sgraph_ai_service_playwright__cli.tui.components.Tui__App                    import Tui__App


class CF_TUI__Screen__Cache(Tui__App):
    TITLE = 'Local Cache · raw-cf-logs'

    def __init__(self, store, **kwargs):
        super().__init__(**kwargs)
        self.store = store

    def populate(self) -> None:
        self.debug_log.record('fs.read', f'scan {self.store.base_dir()}')
        stats = self.store.stats()
        self.debug_log.record('fs.read', f'{stats.total_files} file(s), {stats.day_count} day(s)')
        self.set_body(cache_stats_markup(stats))
