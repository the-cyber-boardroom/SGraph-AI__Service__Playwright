# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: pilot test for the Deployed Architecture screen
# Drives the real Textual app via App.run_test() with an arch source over fake AWS
# clients — no AWS, no mocks. @skipUnless textual; screen imported lazily.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from unittest import TestCase, skipUnless

try:
    import textual                                                                   # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.source.CF_TUI__Arch_Source import CF_TUI__Arch_Source
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.tests.test_CF_TUI__Arch_Source import FakeCF, FakeLogs, FakeS3


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_CF_TUI__Screen__Arch(TestCase):

    def screen(self):
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Screen__Arch import CF_TUI__Screen__Arch
        source = CF_TUI__Arch_Source(cf_client=FakeCF(), logs_client=FakeLogs(), s3_client=FakeS3(), bucket='b')
        return CF_TUI__Screen__Arch(source=source, refresh_seconds=0)

    def test_mounts_and_loads(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.snapshot is not None
            assert len(app.snapshot.distributions) == 2
            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True
