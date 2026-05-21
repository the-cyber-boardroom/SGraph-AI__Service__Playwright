# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Confirm
# A small y/n confirm modal for destructive actions (unregister / teardown). Pushed
# with a callback: push_screen(SG_Edge__TUI__Confirm(message), on_result) where
# on_result(True|False). `y`/Enter confirm, `n`/Esc cancel — never fire a destructive
# action on a single key (separation-guide rule 6 / safety).
# ═══════════════════════════════════════════════════════════════════════════════

from textual.screen  import ModalScreen
from textual.widgets import Static


class SG_Edge__TUI__Confirm(ModalScreen):
    BINDINGS = [('y',      'confirm', 'Yes'),
                ('enter',  'confirm', 'Yes'),
                ('n',      'cancel',  'No'),
                ('escape', 'cancel',  'No')]

    CSS = """
    SG_Edge__TUI__Confirm { align: center middle; }
    #confirm { width: auto; height: auto; padding: 1 2; border: round $warning; background: $panel; }
    """

    def __init__(self, message : str):
        super().__init__()
        self.message = message

    def compose(self):
        yield Static(f'[bold]{self.message}[/]\n\n  [cyan]y[/] confirm    [cyan]n[/] cancel', id='confirm')

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
