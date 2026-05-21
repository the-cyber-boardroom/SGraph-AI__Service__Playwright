# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Bedrock__Chat__Brief__Modal
# Preview a dev brief synthesised from the conversation, then write it (w) or copy it
# to the clipboard (c). Writing lands the brief at the precomputed path the screen
# supplies (under the capture root by default). dismiss(path) on write, dismiss(None)
# on cancel/copy. The "talk to the data → action plan" payoff made concrete.
# ═══════════════════════════════════════════════════════════════════════════════

from pathlib          import Path

from textual.screen      import ModalScreen
from textual.containers  import VerticalScroll
from textual.widgets     import Static


class Bedrock__Chat__Brief__Modal(ModalScreen):
    BINDINGS = [('w',      'write',  'Write'),
                ('c',      'copy',   'Copy'),
                ('escape', 'cancel', 'Cancel'),
                ('q',      'cancel', 'Cancel')]

    CSS = """
    Bedrock__Chat__Brief__Modal { align: center middle; }
    #brief { width: 84; height: 80%; padding: 1 2; border: round $accent; background: $panel; }
    """

    def __init__(self, brief_text: str, write_path: str):
        super().__init__()
        self.brief_text = brief_text
        self.write_path = write_path

    def compose(self):
        def esc(t): return t.replace('[', r'\[')
        head = f'[bold]capture dev brief[/]   [dim]→ {esc(self.write_path)}[/]\n[dim][w] write · [c] copy · esc cancel[/]\n'
        with VerticalScroll(id='brief'):
            yield Static(head + '\n' + esc(self.brief_text))

    def action_write(self) -> None:
        path = Path(self.write_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.brief_text, encoding='utf-8')
        self.app.notify(f'brief written → {path}')
        self.dismiss(str(path))

    def action_copy(self) -> None:
        self.app.copy_to_clipboard(self.brief_text)
        self.app.notify('brief copied to clipboard (OSC-52)')
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)
