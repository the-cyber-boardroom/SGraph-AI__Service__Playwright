# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: pilot tests for Screen 5 (Live Event Stream)
# Drives the real Textual app with an in-memory Local source over a temp stack — no
# mocks. Verifies the first poll seeds (no events), a state change produces a Differ
# event on the next poll, pause halts polling, filter/clear work, q quits.
# @skipUnless textual; screen imported lazily so this module loads on 3.11.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import shutil
import tempfile
from unittest import TestCase, skipUnless

try:
    import textual                                                                   # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

from sg_compute_specs.sg_edge.local.Local__Edge__Stack                  import Local__Edge__Stack
from sg_compute_specs.sg_edge.tui.source.SG_Edge__TUI__Local_Source     import SG_Edge__TUI__Local_Source


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_SG_Edge__TUI__Screen__Events(TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='sg-edge-tui-s5-')
        stack    = Local__Edge__Stack(state_dir=self.dir)
        stack.setup()
        stack.register('alice')
        self.source = SG_Edge__TUI__Local_Source(stack=stack)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def screen(self):
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Events import SG_Edge__TUI__Screen__Events
        return SG_Edge__TUI__Screen__Events(source=self.source, refresh_seconds=0)   # tests poll via `r`

    def test_first_poll_seeds_then_change_emits_event(self):
        asyncio.run(self.scenario_events())

    async def scenario_events(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.events == []                                                  # first poll seeds the baseline
            self.source.register('bob')                                              # state change behind the screen
            await pilot.press('r')                                                   # poll → Differ sees bob
            await pilot.pause()
            kinds = {str(e.kind) for e in app.events}
            assert 'slug_registered' in kinds
            assert any('bob' in e.detail for e in app.events)

    def test_pause_halts_polling(self):
        asyncio.run(self.scenario_pause())

    async def scenario_pause(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press('space')                                               # pause
            assert app.paused is True
            self.source.register('carol')
            await pilot.press('r')                                                   # poll is a no-op while paused
            await pilot.pause()
            assert app.events == []

    def test_clear_and_quit(self):
        asyncio.run(self.scenario_clear_quit())

    async def scenario_clear_quit(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            self.source.register('dave')
            await pilot.press('r')
            await pilot.pause()
            assert app.events != []
            await pilot.press('c')                                                   # clear the feed
            assert app.events == []
            await pilot.press('s')                                                   # filter to slugs
            assert app.active_filter == 'slugs'
            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True
