# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: pilot test for the standalone Field Lineage Inspector
# Drives the real Textual app via App.run_test() with an in-memory source — no mocks.
# @skipUnless textual; the screen is imported lazily so this loads on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from unittest import TestCase, skipUnless

try:
    import textual                                                                   # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__fixtures           import LINE_ENHANCECP
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Fixture_File import Schema__CF_TUI__Fixture_File
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.source.CF_TUI__In_Memory_Source import CF_TUI__In_Memory_Source


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_CF_TUI__Screen__Inspector(TestCase):

    def source(self):
        src = CF_TUI__In_Memory_Source().setup()
        src.files.append(Schema__CF_TUI__Fixture_File(key='logs/a.gz', tsv_text=LINE_ENHANCECP))
        return src

    def screen(self):
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Screen__Inspector import CF_TUI__Screen__Inspector
        return CF_TUI__Screen__Inspector(source=self.source(), key='logs/a.gz', line_index=0)

    def test_mounts_and_loads_record(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.record is not None
            assert app.record.valid is True
            assert {f.name: f for f in app.record.fields}['cs-uri-stem'].value == '/enhancecp'
            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True
