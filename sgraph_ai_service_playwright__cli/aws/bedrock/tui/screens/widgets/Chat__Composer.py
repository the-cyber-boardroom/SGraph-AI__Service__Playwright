# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui widget: Chat__Composer
# A reusable multi-line composer. TextArea has no native submit, so we intercept
# Enter → emit a Submitted message (Shift+Enter / Ctrl+J fall through to a newline).
# Provider-agnostic — a candidate for the shared chat kit. Emits a custom Message so
# the parent screen (which owns the engine) handles the send; the widget stays dumb.
# ═══════════════════════════════════════════════════════════════════════════════

from textual           import events
from textual.message   import Message
from textual.widgets   import TextArea


class Chat__Composer(TextArea):
    DEFAULT_CSS = """
    Chat__Composer { dock: bottom; height: auto; max-height: 10; border: round $accent; }
    """

    class Submitted(Message):
        def __init__(self, text: str):
            self.text = text
            super().__init__()

    def __init__(self, **kwargs):
        super().__init__(soft_wrap=True, tab_behavior='indent', show_line_numbers=False, **kwargs)

    async def _on_key(self, event: events.Key) -> None:
        if event.key == 'enter':
            event.prevent_default()
            event.stop()
            text = self.text.strip()
            if text:
                self.post_message(self.Submitted(text))
                self.text = ''
            return
        await super()._on_key(event)
