# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/screens/user_journey: User_Journey__Cockpit__Screen
# The live cockpit. A thin Tui__App subclass: each refresh fetches the suite snapshot
# from the conductor and renders it via the (pure, tested) cockpit render helper.
# body_markup() holds all the logic and is unit-testable without a running terminal;
# populate() is the only Textual-bound glue. `r` refreshes; refresh_seconds polls.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.tui.components.Tui__App import Tui__App

from sg_compute_specs.user_journey.tui.render.User_Journey__Cockpit__Render import User_Journey__Cockpit__Render


class User_Journey__Cockpit__Screen(Tui__App):

    def __init__(self, conductor=None, suite_run_id: str = '', refresh_seconds: float = 3.0, **kwargs):
        super().__init__(refresh_seconds=refresh_seconds, **kwargs)
        self.conductor     = conductor                                              # a Conductor__Client
        self.suite_run_id  = suite_run_id
        self.render_helper = User_Journey__Cockpit__Render()

    def body_markup(self) -> str:                                                   # pure: fetch + render (no Textual DOM)
        if self.conductor is None or not self.suite_run_id:
            return 'no suite selected'
        status = self.conductor.get_suite(self.suite_run_id)
        if status is None:
            return f'no suite run {self.suite_run_id}'
        return '\n'.join(self.render_helper.lines(status))

    def populate(self) -> None:                                                     # Textual-bound glue only
        try:
            markup = self.body_markup()
        except Exception as error:
            markup = f'error: {error}'
            self.log_event('cockpit', 'fetch failed', str(error), ok=False)
        self.set_body(markup)
