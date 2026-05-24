# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for the Traffic TUI (pure render + Textual pilot)
# Render is 3.11-safe. The pilot drives the real generator (node) — node-gated.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from unittest import TestCase, skipUnless

from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Corpus           import Sentinel__Traffic__Corpus
from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Generator        import Sentinel__Traffic__Generator
from sgraph_ai_service_playwright__cli.sentinel.traffic.service.Sentinel__Traffic__Report__Builder  import Sentinel__Traffic__Report__Builder
from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Traffic__Render          import traffic_markup, traffic_plain

try:
    import textual                                                                   # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source    import node_available
from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Local__Harness import Sentinel__Local__Harness
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.InMemory__Log__Sink   import InMemory__Log__Sink


class TestRender(TestCase):
    def test_idle_shows_corpus_and_no_run(self):
        out = traffic_markup(Sentinel__Traffic__Corpus().cases(), None, [])
        assert 'CORPUS' in out and 'benign' in out and 'no run yet' in out

    def test_report_shows_accuracy_and_cases(self):
        if not node_available():
            self.skipTest('node not available')
        gen     = Sentinel__Traffic__Generator(harness=Sentinel__Local__Harness(log_sink=InMemory__Log__Sink()))
        cases   = Sentinel__Traffic__Corpus().cases()
        results = gen.run_local(cases)
        report  = Sentinel__Traffic__Report__Builder().build(results, mode='local')
        out     = traffic_markup(cases, report, results)
        assert '100.0%' in out and 'etc-passwd' in out and 'REPORT' in out

    def test_plain_no_markup(self):
        assert traffic_plain(None, []) == 'SG/Sentinel traffic: no run.'


@skipUnless(HAS_TEXTUAL and node_available(), 'textual + node required')
class test_Traffic_Screen(TestCase):
    def test_run_then_reset(self):
        asyncio.run(self._scenario())

    async def _scenario(self):
        from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Screen__Traffic import Sentinel__TUI__Screen__Traffic
        gen = Sentinel__Traffic__Generator(harness=Sentinel__Local__Harness(log_sink=InMemory__Log__Sink()))
        app = Sentinel__TUI__Screen__Traffic(generator=gen)
        async with app.run_test(size=(110, 40)) as pilot:
            await pilot.pause()
            assert app.report is None
            await pilot.press('g')
            await pilot.pause()
            assert app.report is not None and app.report.accuracy_pct == 100.0
            await pilot.press('r')
            await pilot.pause()
            assert app.report is None
            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True
