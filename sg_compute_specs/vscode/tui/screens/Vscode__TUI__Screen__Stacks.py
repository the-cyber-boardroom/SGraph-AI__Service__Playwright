# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode tui: Vscode__TUI__Screen__Stacks
# The read-only stacks dashboard. Subclasses the shared Tui__App (Header + scrollable
# body + Debug Panel + Footer come free); populate() reads the data source and drops
# the pure markup into the body. No logic lives here — the source delegates to
# Vscode__Service (the same backend `sg vscode list` uses). Imports Textual, so it
# is only imported lazily from the CLI command body.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.tui.components.Tui__App           import Tui__App

from sg_compute_specs.vscode.tui.service.Vscode__TUI__Render             import Vscode__TUI__Render


class Vscode__TUI__Screen__Stacks(Tui__App):
    TITLE = 'sg vscode — stacks'

    def __init__(self, source, **kwargs):
        super().__init__(refresh_seconds=kwargs.pop('refresh_seconds', 5.0), **kwargs)
        self.source = source
        self.render = Vscode__TUI__Render()

    def populate(self) -> None:
        snapshot = self.source.snapshot()
        self.set_body(self.render.stacks_markup(snapshot))
        self.log_event('vscode', 'snapshot', f'{snapshot.total} stack(s) in {snapshot.region}', ok=True)
