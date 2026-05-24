# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — pilot tests for the Sentinel TUI screens (real Textual app, no AWS/node)
# Drives the screens via App.run_test() with an in-memory source. @skipUnless textual.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from unittest import TestCase, skipUnless

try:
    import textual                                                                   # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Log_Record import Schema__Sentinel__Log_Record
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink  import InMemory__Log__Sink
from sgraph_ai_service_playwright__cli.sentinel.tui.source.Sentinel__TUI__Source      import Sentinel__TUI__Source


def _source():
    sink = InMemory__Log__Sink()
    sink.write(Schema__Sentinel__Log_Record(request_id='sn-1', received_at='2026-05-23T14:30:00Z', method='GET',
                                            path='/etc/passwd', host='h', source_ip='abc', verdict='block',
                                            reason='path never valid', rule_id='0012', http_status=403, enforced=True))
    return Sentinel__TUI__Source(log_sink=sink)


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_Rules_Screen(TestCase):
    def test_select_detail_back_quit(self):
        asyncio.run(self._scenario())

    async def _scenario(self):
        from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Screen__Rules import Sentinel__TUI__Screen__Rules
        app = Sentinel__TUI__Screen__Rules(source=_source())
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.mode == 'list' and len(app.rules) == 6
            await pilot.press('down'); await pilot.press('down')
            await pilot.pause()
            assert app.index == 2
            await pilot.press('enter')
            await pilot.pause()
            assert app.mode == 'detail'
            await pilot.press('escape')
            await pilot.pause()
            assert app.mode == 'list'
            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_Logs_Screen(TestCase):
    def test_trace_then_blocks(self):
        asyncio.run(self._scenario())

    async def _scenario(self):
        from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Screen__Logs import Sentinel__TUI__Screen__Logs
        app = Sentinel__TUI__Screen__Logs(source=_source(), sink_label='in-memory')
        async with app.run_test() as pilot:
            await pilot.pause()
            assert len(app.records) == 1
            await pilot.press('enter')
            await pilot.pause()
            assert app.mode == 'trace'
            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_Blocks_And_Status_Screens(TestCase):
    def test_they_mount_and_quit(self):
        asyncio.run(self._scenario())

    async def _scenario(self):
        from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Screen__Blocks import Sentinel__TUI__Screen__Blocks
        from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Screen__Status import Sentinel__TUI__Screen__Status
        for app in (Sentinel__TUI__Screen__Blocks(source=_source()),
                    Sentinel__TUI__Screen__Status(source=_source(), sink_label='in-memory')):
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press('q')
                await pilot.pause()
                assert app.exited is True
