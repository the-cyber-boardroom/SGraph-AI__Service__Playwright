# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: pilot tests for the Files browser (folder → file → record)
# Drives the real Textual app via App.run_test() with an in-memory source holding two
# named blobs under a folder — no mocks. Verifies: mount lists the folder, Enter
# descends, Enter opens a file, Enter inspects a record's fields, Esc walks back up,
# q exits. @skipUnless textual; the screen is imported lazily so this loads on 3.11.
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
        src.files.append(Schema__CF_TUI__Fixture_File(key='logs/a.gz', tsv_text=LINE_ENHANCECP))
        src.files.append(Schema__CF_TUI__Fixture_File(key='logs/b.gz', tsv_text=LINE_ROBOTS))
        return src

    def screen(self):
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Screen__Files import CF_TUI__Screen__Files
        return CF_TUI__Screen__Files(source=self.make_source(), start_prefix='', refresh_seconds=0)

    def test_mounts_at_dir_root(self):
        asyncio.run(self.scenario_root())

    async def scenario_root(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.mode == 'dir'
            assert [e.name for e in app.entries] == ['logs/']
            assert app.entries[0].is_folder is True

    def test_descend_open_inspect_and_back(self):
        asyncio.run(self.scenario_drill())

    async def scenario_drill(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press('enter')                                               # descend into logs/
            await pilot.pause()
            assert app.prefix == 'logs/'
            assert {e.name for e in app.entries} == {'a.gz', 'b.gz'}

            await pilot.press('enter')                                               # open the first file
            await pilot.pause()
            assert app.mode == 'file'
            assert app.view.total_events == 1

            await pilot.press('enter')                                               # inspect the selected event's fields
            await pilot.pause()
            assert app.mode == 'record'
            assert app.record.valid is True

            await pilot.press('escape')                                              # record → file
            await pilot.pause()
            assert app.mode == 'file'
            await pilot.press('escape')                                              # file → dir (logs/)
            await pilot.pause()
            assert app.mode == 'dir' and app.prefix == 'logs/'
            await pilot.press('escape')                                              # dir up → root
            await pilot.pause()
            assert app.prefix == ''

    def test_raw_toggle_in_file(self):
        asyncio.run(self.scenario_raw())

    async def scenario_raw(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press('enter')                                               # into logs/
            await pilot.press('enter')                                               # open a.gz
            await pilot.pause()
            assert app.raw is False
            await pilot.press('t')
            assert app.raw is True

    def test_quit(self):
        asyncio.run(self.scenario_quit())

    async def scenario_quit(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True
