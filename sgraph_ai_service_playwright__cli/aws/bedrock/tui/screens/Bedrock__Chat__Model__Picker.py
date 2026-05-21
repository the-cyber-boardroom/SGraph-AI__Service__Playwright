# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Bedrock__Chat__Model__Picker
# Nova-only model picker (the brief's "start with only Nova"). A ModalScreen[str]
# returning the chosen alias. Pricing columns come straight from the existing cost
# calculator. ↑/↓ move, Enter selects, Esc cancels. Switching keeps the conversation.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.screen  import ModalScreen
from textual.widgets import Static


class Bedrock__Chat__Model__Picker(ModalScreen[str]):
    BINDINGS = [('up',     'cursor_up',   'Up'),
                ('k',      'cursor_up',   'Up'),
                ('down',   'cursor_down', 'Down'),
                ('j',      'cursor_down', 'Down'),
                ('enter',  'select',      'Select'),
                ('escape', 'cancel',      'Cancel'),
                ('q',      'cancel',      'Cancel')]

    CSS = """
    Bedrock__Chat__Model__Picker { align: center middle; }
    #picker { width: auto; height: auto; padding: 1 2; border: round $accent; background: $panel; }
    """

    def __init__(self, rows: list, current: str = 'default'):
        super().__init__()
        self.rows     = rows                                                      # [(alias, model_id, in_price, out_price), ...]
        self.selected = next((i for i, r in enumerate(rows) if r[0] == current), 0)

    def compose(self):
        yield Static(self._markup(), id='picker')

    def _markup(self) -> str:
        lines = ['[bold]choose a Nova model[/]', '',
                 f'  [dim]{"alias":<9}{"model id":<26}{"in $/1M":>9}{"out $/1M":>10}[/]']
        for i, (alias, model_id, in_p, out_p) in enumerate(self.rows):
            marker = '[cyan]▸[/]' if i == self.selected else ' '
            style  = 'bold' if i == self.selected else 'default'
            lines.append(f' {marker} [{style}]{alias:<9}{model_id:<26}{in_p:>9}{out_p:>10}[/]')
        lines += ['', '[dim]↑/↓ move · Enter select · Esc cancel — switching keeps the chat[/]']
        return '\n'.join(lines)

    def _rerender(self):
        self.query_one('#picker', Static).update(self._markup())

    def action_cursor_down(self):
        if self.rows:
            self.selected = min(self.selected + 1, len(self.rows) - 1)
            self._rerender()

    def action_cursor_up(self):
        if self.rows:
            self.selected = max(self.selected - 1, 0)
            self._rerender()

    def action_select(self):
        if self.rows:
            self.dismiss(self.rows[self.selected][0])

    def action_cancel(self):
        self.dismiss(None)
