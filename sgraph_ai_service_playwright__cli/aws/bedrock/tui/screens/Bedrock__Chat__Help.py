# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Bedrock__Chat__Help
# Context-aware help overlay (the `?` keypress) — a ModalScreen listing the screen's
# keybindings, fed (key, description) pairs walked off the App's MRO. Same pattern as
# the sg_edge / cf TUIs. Dismiss with ? / esc / q.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.screen  import ModalScreen
from textual.widgets import Static


class Bedrock__Chat__Help(ModalScreen):
    BINDINGS = [('escape',        'dismiss_help', 'Close'),
                ('question_mark', 'dismiss_help', 'Close'),
                ('q',             'dismiss_help', 'Close')]

    CSS = """
    Bedrock__Chat__Help { align: center middle; }
    #help { width: auto; height: auto; padding: 1 2; border: round $accent; background: $panel; }
    """

    def __init__(self, lines: list):
        super().__init__()
        self.lines = lines

    def compose(self):
        body = ['[bold]sg aws bedrock chat — keys[/]', '']
        for key, desc in self.lines:
            label = {'enter': 'enter', 'question_mark': '?', 'space': 'space',
                     'ctrl+l': '^L'}.get(key, key)
            body.append(f'  [cyan]{label:<8}[/] {desc}')
        body += ['', '[dim]? / esc to close[/]']
        yield Static('\n'.join(body), id='help')

    def action_dismiss_help(self) -> None:
        self.dismiss()
