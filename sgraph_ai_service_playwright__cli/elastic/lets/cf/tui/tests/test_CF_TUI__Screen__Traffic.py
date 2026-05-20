# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: pilot tests for Screen 5 (Traffic Reality)
# Drives the real Textual app via App.run_test() with an in-memory source over the
# golden fixtures — no mocks. Verifies the wiring: mount loads a snapshot, `e` exports
# a card, `q` exits. @skipUnless textual (gated like the CLI suites gate on typer);
# the screen is imported lazily so this module loads on 3.11 even without textual.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import os
import tempfile
from unittest import TestCase, skipUnless

try:
    import textual                                                                   # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__fixtures           import FIXTURE_TSV
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.source.CF_TUI__In_Memory_Source import CF_TUI__In_Memory_Source


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_CF_TUI__Screen__Traffic(TestCase):

    def setUp(self):
        self.source = CF_TUI__In_Memory_Source(tsv_text=FIXTURE_TSV).setup()

    def screen(self):
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Screen__Traffic import CF_TUI__Screen__Traffic
        return CF_TUI__Screen__Traffic(source=self.source, refresh_seconds=0)         # 0 → no timer; tests drive refresh

    def test_mounts_and_loads_snapshot(self):
        asyncio.run(self.scenario_mounts())

    async def scenario_mounts(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            from textual.widgets import Static
            assert app.snapshot is not None
            assert app.snapshot.total_events == 2
            assert app.query_one('#body', Static) is not None

    def test_export_writes_card(self):
        asyncio.run(self.scenario_export())

    async def scenario_export(self):
        cwd = os.getcwd()
        tmp = tempfile.mkdtemp(prefix='cf-tui-s5-')
        os.chdir(tmp)
        try:
            app = self.screen()
            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press('e')
                await pilot.pause()
                assert app.exported_path == 'cf-traffic-card.txt'
                assert os.path.exists(os.path.join(tmp, 'cf-traffic-card.txt'))
        finally:
            os.chdir(cwd)

    def test_quit_key_exits(self):
        asyncio.run(self.scenario_quit())

    async def scenario_quit(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True
