# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: pilot tests for Screen 2 (Topology)
# Drives the real Textual app with an in-memory Local source over a temp stack — no
# mocks. Verifies mount, ↑/↓ selection navigation (with clamping), r refresh, q quit.
# @skipUnless textual; the screen is imported lazily so this module loads on 3.11.
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
class test_SG_Edge__TUI__Screen__Topology(TestCase):

    def setUp(self):
        self.dir   = tempfile.mkdtemp(prefix='sg-edge-tui-s2-')
        stack      = Local__Edge__Stack(state_dir=self.dir)
        stack.setup()
        stack.register('alice')
        stack.register('bob')
        self.source = SG_Edge__TUI__Local_Source(stack=stack)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def screen(self):
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Topology import SG_Edge__TUI__Screen__Topology
        return SG_Edge__TUI__Screen__Topology(source=self.source, refresh_seconds=0)

    def test_navigation_clamps(self):
        asyncio.run(self.scenario_nav())

    async def scenario_nav(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.selected_index == 0                                           # default selection on the first slug
            assert len(app.snapshot.slugs) == 2
            await pilot.press('down')
            assert app.selected_index == 1
            await pilot.press('down')                                                # clamp at the last slug
            assert app.selected_index == 1
            await pilot.press('up')
            assert app.selected_index == 0
            await pilot.press('up')                                                  # clamp at the first slug
            assert app.selected_index == 0

    def test_enter_drills_into_selected_slug(self):
        asyncio.run(self.scenario_drill())

    async def scenario_drill(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press('down')                                                # select the 2nd slug
            await pilot.press('enter')
            await pilot.pause()
        assert app.opened_slug == app.snapshot.slugs[1].slug                         # recorded for the CLI to open Slug detail

    def test_refresh_and_quit(self):
        asyncio.run(self.scenario_refresh_quit())

    async def scenario_refresh_quit(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            self.source.register('carol')
            await pilot.press('r')
            await pilot.pause()
            assert len(app.snapshot.slugs) == 3
            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True
