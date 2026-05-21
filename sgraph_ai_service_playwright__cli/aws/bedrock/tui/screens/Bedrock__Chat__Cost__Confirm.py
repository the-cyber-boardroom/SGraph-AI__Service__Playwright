# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Bedrock__Chat__Cost__Confirm
# Blocking confirm before an over-cap send. dismiss(True) to proceed (the screen then
# sends with an explicit override), dismiss(False) to cancel. Never a silent overspend.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.screen  import ModalScreen
from textual.widgets import Static


class Bedrock__Chat__Cost__Confirm(ModalScreen[bool]):
    BINDINGS = [('y',      'confirm', 'Proceed'),
                ('enter',  'confirm', 'Proceed'),
                ('n',      'cancel',  'Cancel'),
                ('escape', 'cancel',  'Cancel')]

    CSS = """
    Bedrock__Chat__Cost__Confirm { align: center middle; }
    #confirm { width: auto; max-width: 70; height: auto; padding: 1 2; border: round $warning; background: $panel; }
    """

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self):
        body = ['[bold yellow]Cost cap[/]', '', self.message, '',
                '[dim][y]/enter proceed   [n]/esc cancel[/]']
        yield Static('\n'.join(body), id='confirm')

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
