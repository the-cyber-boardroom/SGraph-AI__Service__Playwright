# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Bedrock__Chat__Doc__Picker
# A ModalScreen to attach a document to the next message. Type a path, Enter loads it
# via Bedrock__Chat__Documents (format + size validated) and dismisses with the
# Schema__Bedrock__Chat__Document; an invalid file shows the error inline. Esc cancels.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.containers import Vertical
from textual.screen     import ModalScreen
from textual.widgets    import Input, Static


class Bedrock__Chat__Doc__Picker(ModalScreen):
    BINDINGS = [('escape', 'cancel', 'Cancel')]

    CSS = """
    Bedrock__Chat__Doc__Picker { align: center middle; }
    #box { width: 72; height: auto; padding: 1 2; border: round $accent; background: $panel; }
    #err { color: $error; }
    """

    def compose(self):
        with Vertical(id='box'):
            yield Static('[bold]attach a document[/]\n[dim]pdf · txt · md · csv · docx · html · xls(x) · ≤ 4.5 MB[/]')
            yield Input(placeholder='path to file…', id='path')
            yield Static('', id='err')

    def on_mount(self):
        self.query_one('#path', Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        path = (event.value or '').strip()
        if not path:
            return
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Documents import Bedrock__Chat__Documents
        try:
            document = Bedrock__Chat__Documents().load(path)
        except Exception as exc:
            self.query_one('#err', Static).update(f'{type(exc).__name__}: {exc}')
            return
        self.dismiss(document)

    def action_cancel(self):
        self.dismiss(None)
