# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__TUI__Dashboard
# One app, all surfaces (Rules / Logs / Blocks / Status / Traffic tabs) + ONE shared
# chat pane docked on the right, so the conversation has continuity as you switch
# tabs. The chat is the read-only Sentinel__Chat (Bedrock Nova) driving the TUI API —
# it can answer about anything on screen and run traffic_gen, but changes nothing.
#
# The blocking LLM call runs in a Textual worker (asyncio.to_thread) so the UI never
# freezes. Inject a Sentinel__Chat with a scripted backend in tests (no AWS/LLM); pass
# chat=None to run as a pure viewer.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio

from textual            import work, on
from textual.app        import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets    import Header, Footer, Static, TabbedContent, TabPane

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.widgets.Chat__Bubble        import Chat__Bubble
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.widgets.Chat__Composer      import Chat__Composer
from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__App__Base        import Sentinel__TUI__App__Base
from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Rules__Render    import rules_markup
from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Logs__Render     import logs_markup
from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Blocks__Render   import blocks_markup
from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Status__Render   import status_markup
from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Traffic__Render  import traffic_markup
from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Corpus   import Sentinel__Traffic__Corpus


class Sentinel__TUI__Dashboard(Sentinel__TUI__App__Base):
    TITLE    = 'SG/Sentinel'
    BINDINGS = [('r', 'refresh', 'Refresh')]
    CSS = """
    #main { height: 1fr; }
    #tabs { width: 2fr; }
    #chat { width: 1fr; border-left: round $accent; }
    #chat_transcript { height: 1fr; }
    #chat_hint { color: $text-muted; padding: 0 1; }
    """

    def __init__(self, source, chat=None, sink_label: str = '(local)'):
        super().__init__()
        self.source     = source
        self.chat       = chat                                                       # Sentinel__Chat | None
        self.sink_label = sink_label
        self.session    = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id='main'):
            with TabbedContent(id='tabs'):
                with TabPane('Rules',   id='tab_rules'):   yield VerticalScroll(Static('', id='body_rules'))
                with TabPane('Logs',    id='tab_logs'):    yield VerticalScroll(Static('', id='body_logs'))
                with TabPane('Blocks',  id='tab_blocks'):  yield VerticalScroll(Static('', id='body_blocks'))
                with TabPane('Status',  id='tab_status'):  yield VerticalScroll(Static('', id='body_status'))
                with TabPane('Traffic', id='tab_traffic'): yield VerticalScroll(Static('', id='body_traffic'))
            with Vertical(id='chat'):
                yield Static('[bold]Chat[/]  [dim](Nova · read-only)[/]', id='chat_hint')
                yield VerticalScroll(id='chat_transcript')
                yield Chat__Composer(id='composer')
        yield Footer()

    def on_mount(self) -> None:
        self.action_refresh()
        if self.chat is not None:
            self.session = self.chat.new_session()
        else:
            self.query_one('#chat_hint', Static).update('[bold]Chat[/]  [dim](disabled — no backend)[/]')

    def action_refresh(self) -> None:
        self.query_one('#body_rules',   Static).update(rules_markup(list(self.source.rules())))
        self.query_one('#body_logs',    Static).update(logs_markup(list(self.source.records()), self.sink_label))
        groups = self.source.block_groups()
        self.query_one('#body_blocks',  Static).update(blocks_markup(groups, sum(g.count for g in groups)))
        self.query_one('#body_status',  Static).update(status_markup(self.source.status(), self.sink_label, self.source.engine_code()))
        self.query_one('#body_traffic', Static).update(traffic_markup(list(Sentinel__Traffic__Corpus().cases()), None, []))

    @on(Chat__Composer.Submitted)
    def _on_submitted(self, message: Chat__Composer.Submitted) -> None:
        self._chat_worker(message.text)

    @work(exclusive=True, group='chat')
    async def _chat_worker(self, text: str) -> None:
        transcript = self.query_one('#chat_transcript', VerticalScroll)
        await transcript.mount(Chat__Bubble('user', text, author='you'))
        transcript.scroll_end()
        if self.chat is None or self.session is None:
            await transcript.mount(Chat__Bubble('assistant', 'chat backend not configured', author='system'))
            return
        try:
            turn   = await asyncio.to_thread(self.chat.ask, self.session, text)
            answer = turn.response_text or '(no response)'
            if turn.tool_calls:                                                      # bubble renders Markdown — plain/italic, no Rich tags
                answer += f'\n\n_· used {turn.tool_calls} tool call(s) · ${round(turn.cost_usd, 5)}_'
        except Exception as exc:                                                     # honest failure (e.g. no AWS creds), never a crash
            answer = f'**error:** {type(exc).__name__}: {exc}'
        bubble = Chat__Bubble('assistant', '', author='nova')
        await transcript.mount(bubble)
        bubble.set_body(answer)
        transcript.scroll_end()
