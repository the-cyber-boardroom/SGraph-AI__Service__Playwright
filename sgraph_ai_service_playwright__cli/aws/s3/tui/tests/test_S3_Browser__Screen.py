# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — s3 tui: pilot test for the S3 browser screen
# Drives the real Textual app via App.run_test() with the fake-client source — no
# AWS, no mocks. buckets → dir → object → back → quit. @skipUnless textual.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from unittest import TestCase, skipUnless

try:
    import textual                                                                   # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

from sgraph_ai_service_playwright__cli.aws.s3.tui.tests.test_S3_Browser__Source import source


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_S3_Browser__Screen(TestCase):

    def screen(self):
        from sgraph_ai_service_playwright__cli.aws.s3.tui.screens.S3_Browser__Screen import S3_Browser__Screen
        return S3_Browser__Screen(source=source(), refresh_seconds=0)

    def test_browse_buckets_to_object(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.mode == 'buckets'
            assert {e.name for e in app.entries} == {'bucket-1', 'bucket-2'}

            await pilot.press('enter')                                               # open bucket-1 → dir
            await pilot.pause()
            assert app.mode == 'dir'
            assert {e.name for e in app.entries} == {'logs/', 'a.json'}

            # select the file 'a.json' and open it
            idx = [e.name for e in app.entries].index('a.json')
            while app.selected < idx:
                await pilot.press('down')
            await pilot.press('enter')
            await pilot.pause()
            assert app.mode == 'object'
            assert '"x"' in app.view.text

            await pilot.press('escape')                                              # object → dir
            await pilot.pause()
            assert app.mode == 'dir'
            await pilot.press('escape')                                              # dir → buckets
            await pilot.pause()
            assert app.mode == 'buckets'

            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True
