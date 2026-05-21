# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: pilot test for the sync screen
# Drives the real Textual app with fake S3 boundaries + a tmp store — no AWS, no
# mocks. Asserts the plan renders, the Debug Panel shares the sync log, and pressing
# `g` runs the thread worker to download the missing objects (then files flip to ✓).
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import tempfile
from unittest import TestCase, skipUnless

try:
    import textual                                                                   # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.service.CF__Local__Store import CF__Local__Store
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.service.CF__Logs__Sync   import CF__Logs__Sync
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.tests.test_CF__Logs__Sync import FakeLister, FakeFetcher, PREFIX
from sgraph_ai_service_playwright__cli.tui.debug.Debug__Event_Log                     import Debug__Event_Log


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_CF_TUI__Screen__Sync(TestCase):

    def test_plan_then_download(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Screen__Sync import CF_TUI__Screen__Sync
        from sgraph_ai_service_playwright__cli.tui.components.Debug__Panel             import Debug__Panel
        with tempfile.TemporaryDirectory() as tmp:
            svc = CF__Logs__Sync(lister=FakeLister(), fetcher=FakeFetcher(),
                                 store=CF__Local__Store(root=tmp, src_prefix=PREFIX), debug=Debug__Event_Log())
            app = CF_TUI__Screen__Sync(sync=svc, date_iso='2026-05-21', refresh_seconds=0)
            async with app.run_test() as pilot:
                await pilot.pause()
                assert app.plan.missing_count == 3
                assert app.debug_log is svc.debug                                    # panel shares the sync feed
                assert app.query_one('#debug-panel', Debug__Panel).has_class('-hidden') is False

                await pilot.press('g')                                               # download missing
                await app.workers.wait_for_complete()
                await pilot.pause()
                assert app.result.downloaded == 3
                assert app.plan.missing_count == 0                                   # re-planned: all present now

                await pilot.press('q')
                await pilot.pause()
                assert app.exited is True
