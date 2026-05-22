# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui widget: Chat__Bubble
# A reusable chat message bubble: a Markdown body + a Static footer (cost line),
# role-styled via scoped DEFAULT_CSS. Provider-agnostic — knows nothing about Bedrock;
# a candidate for promotion to _shared/tui/chat/ (the sixth conversation). The body
# streams via set_body() (called from the worker through call_from_thread).
# ═══════════════════════════════════════════════════════════════════════════════

from textual.containers import Vertical
from textual.widgets    import Markdown, Static


class Chat__Bubble(Vertical):
    DEFAULT_CSS = """
    Chat__Bubble { height: auto; margin: 1 2 0 2; padding: 0 1; border: round $surface; }
    Chat__Bubble.-user      { border: round $primary;  }
    Chat__Bubble.-assistant { border: round $success;  }
    Chat__Bubble .body   { height: auto; }
    Chat__Bubble .footer { height: auto; color: $text-muted; }
    """

    def __init__(self, role: str, text: str = '', author: str = ''):
        super().__init__()
        self.role     = role
        self._initial = text
        self.author   = author or role
        self.add_class(f'-{role}')

    def compose(self):
        yield Static(f'[dim]{self.author}[/]', classes='author')
        yield Markdown(self._initial, classes='body')
        yield Static('', classes='footer')

    def set_body(self, text: str):                                                # returns the update awaitable so call_from_thread awaits it
        return self.query_one('.body', Markdown).update(text)

    def set_footer(self, markup: str):
        self.query_one('.footer', Static).update(markup)

    def body_text(self) -> str:                                                   # for tests
        return self.query_one('.body', Markdown).source
