# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui widget: Chat__Inspector
# An openable right-hand panel: a list of the session's requests + the EXACT Converse
# request body and response for the selected one. Thin — fed by the PURE inspector
# render helpers; holds no logic. Hidden by default (the screen toggles `display` and
# swaps it with the cost meter). Makes "is the history being sent?" self-evident — the
# full messages array is right there in the request JSON.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.containers import Vertical, VerticalScroll
from textual.widgets    import Static

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Render import (inspector_list_markup,
                                                                                             inspector_detail_markup)


class Chat__Inspector(Vertical):
    DEFAULT_CSS = """
    Chat__Inspector { dock: right; width: 64; border: round $accent; padding: 0 1; }
    Chat__Inspector #ins-list { height: auto; max-height: 30%; }
    Chat__Inspector #ins-detail-scroll { height: 1fr; }
    """

    def compose(self):
        yield Static('', id='ins-list')
        with VerticalScroll(id='ins-detail-scroll'):
            yield Static('', id='ins-detail')

    def refresh_from(self, session, selected: int) -> None:
        turns = list(session.turns)
        self.query_one('#ins-list', Static).update(inspector_list_markup(turns, selected))
        turn = turns[selected] if (turns and 0 <= selected < len(turns)) else None
        self.query_one('#ins-detail', Static).update(inspector_detail_markup(turn, selected))
