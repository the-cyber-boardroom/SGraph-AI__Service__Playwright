# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: pilot tests for the Files browser (S3 browser)
# Drives the real Textual app via App.run_test() with an in-memory source holding two
# named blobs of real CF lines — no mocks. Verifies: mount lists files, ↓ moves the
# cursor, Enter opens a file (inspect mode), `t` toggles raw, Esc returns, `q` exits.
# @skipUnless textual; the screen is imported lazily so this module loads on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from unittest import TestCase, skipUnless

try:
    import textual                                                                   # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__fixtures           import LINE_ENHANCECP, LINE_ROBOTS
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Fixture_File import Schema__CF_TUI__Fixture_File
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.source.CF_TUI__In_Memory_Source import CF_TUI__In_Memory_Source


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_CF_TUI__Screen__Files(TestCase):

    def make_source(self):
        src = CF_TUI__In_Memory_Source().setup()
        src.files.append(Schema__CF_TUI__Fixture_File(key='file-a.gz', tsv_text=LINE_ENHANCECP))
        src.files.append(Schema__CF_TUI__Fixture_File(key='file-b.gz', tsv_text=LINE_ROBOTS))
        return src

    def screen(self):
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Screen__Files import CF_TUI__Screen__Files
        return CF_TUI__Screen__Files(source=self.make_source(), refresh_seconds=0)

    def test_mounts_and_lists(self):
        asyncio.run(self.scenario_list())

    async def scenario_list(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.mode == 'browse'
            assert {r.key for r in app.rows} == {'file-a.gz', 'file-b.gz'}

    def test_navigate_open_toggle_back(self):
        asyncio.run(self.scenario_drill())

    async def scenario_drill(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press('down')                                                # select second file
            assert app.selected == 1
            await pilot.press('enter')                                               # open it
            await pilot.pause()
            assert app.mode == 'inspect'
            assert app.view is not None
            assert app.view.total_events == 1
            assert app.raw is False
            await pilot.press('t')                                                    # raw toggle
            assert app.raw is True
            await pilot.press('escape')                                               # back to browse
            await pilot.pause()
            assert app.mode == 'browse'

    def test_quit(self):
        asyncio.run(self.scenario_quit())

    async def scenario_quit(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True
