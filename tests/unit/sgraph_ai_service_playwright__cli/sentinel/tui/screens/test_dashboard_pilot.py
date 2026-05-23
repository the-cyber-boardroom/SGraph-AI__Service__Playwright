# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — pilot test for the shared-pane dashboard (Textual; scripted chat, no AWS)
# Asserts the tabs are populated AND the one shared chat pane answers a question by
# running a real Sentinel tool against live in-memory state. @skipUnless textual.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from unittest import TestCase, skipUnless

try:
    import textual                                                                   # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Log_Record   import Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink    import InMemory__Log__Sink
from sgraph_ai_service_playwright__cli.sentinel.tui.chat.Sentinel__Chat                 import Sentinel__Chat
from sgraph_ai_service_playwright__cli.sentinel.tui.source.Sentinel__TUI__Source        import Sentinel__TUI__Source
from sgraph_ai_service_playwright__cli.sentinel.tui.tui_api.Sentinel__Tui_Api__Provider import SLUG
from sgraph_ai_service_playwright__cli.tui.chat.backend.Chat__Backend__In_Memory        import Chat__Backend__In_Memory
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Content           import Schema__Chat__Content
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Tool_Use          import Schema__Chat__Tool_Use
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Turn__Result      import Schema__Chat__Turn__Result
from sgraph_ai_service_playwright__cli.tui.chat.schemas.Schema__Chat__Usage             import Schema__Chat__Usage
from sgraph_ai_service_playwright__cli.tui.chat.service.Chat__Tool__Builder             import Chat__Tool__Builder


def _source():
    sink = InMemory__Log__Sink()
    sink.write(Schema__Sentinel__Log_Record(request_id='sn-1', received_at='2026-05-23T14:30:00Z', method='GET',
                                            path='/etc/passwd', host='h', source_ip='abc', verdict='block',
                                            reason='path never valid', rule_id='0012', http_status=403, enforced=True))
    return Sentinel__TUI__Source(log_sink=sink)


def _scripted_chat(source):
    name = Chat__Tool__Builder().tool_name(SLUG, 'blocks_list')
    use  = Schema__Chat__Turn__Result(stop_reason='tool_use', usage=Schema__Chat__Usage(input_tokens=10, output_tokens=5, latency_ms=5))
    use.content.append(Schema__Chat__Content(tool_use=Schema__Chat__Tool_Use(id='t1', name=name, input={})))
    end  = Schema__Chat__Turn__Result(stop_reason='end_turn', usage=Schema__Chat__Usage(input_tokens=12, output_tokens=8, latency_ms=6))
    end.content.append(Schema__Chat__Content(text='There is 1 block (rule 0012).'))
    backend = Chat__Backend__In_Memory()
    backend.scripted_turns = [use, end]
    return Sentinel__Chat(source=source, backend=backend)


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_Dashboard(TestCase):
    def test_tabs_populated_and_shared_chat_answers(self):
        asyncio.run(self._scenario())

    async def _scenario(self):
        from textual.widgets import Static
        from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Dashboard import Sentinel__TUI__Dashboard
        from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Dashboard import Chat__Composer, Chat__Bubble

        source = _source()
        app    = Sentinel__TUI__Dashboard(source=source, chat=_scripted_chat(source))
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            assert app.session is not None                                           # one shared session for the app
            assert '0012' in str(app.query_one('#body_rules',  Static).render())     # rules tab populated
            assert 'path never valid' in str(app.query_one('#body_blocks', Static).render())

            composer = app.query_one('#composer', Chat__Composer)
            composer.focus()
            await pilot.pause()
            composer.text = 'how many blocks?'
            await pilot.press('enter')                                               # composer → Submitted → worker
            await pilot.pause()
            await app.workers.wait_for_complete()
            await pilot.pause()

            bubbles = list(app.query(Chat__Bubble))
            assert len(bubbles) >= 2                                                  # user + assistant in the shared pane

            app.set_focus(None)                                                       # leave the composer so 'q' hits the app binding
            await pilot.pause()
            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True
