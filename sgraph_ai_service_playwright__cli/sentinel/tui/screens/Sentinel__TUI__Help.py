# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__TUI__Help
# Context-aware help overlay (the `?` keypress): a ModalScreen listing the active
# screen's keybindings. Dismiss with ? / esc / q.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.screen  import ModalScreen
from textual.widgets import Static


class Sentinel__TUI__Help(ModalScreen):
    BINDINGS = [('escape',        'dismiss_help', 'Close'),
                ('question_mark', 'dismiss_help', 'Close'),
                ('q',             'dismiss_help', 'Close')]

    CSS = """
    Sentinel__TUI__Help { align: center middle; }
    #help { width: auto; height: auto; padding: 1 2; border: round $accent; background: $panel; }
    """

    def __init__(self, lines: list):
        super().__init__()
        self.lines = lines

    def compose(self):
        body = ['[bold]Keybindings[/]', '']
        for key, desc in self.lines:
            label = {'question_mark': '?', 'space': 'space', 'enter': 'enter'}.get(key, key)
            body.append(f'  [cyan]{label:<8}[/] {desc}')
        body += ['', '[dim]? / esc to close[/]']
        yield Static('\n'.join(body), id='help')

    def action_dismiss_help(self) -> None:
        self.dismiss()
