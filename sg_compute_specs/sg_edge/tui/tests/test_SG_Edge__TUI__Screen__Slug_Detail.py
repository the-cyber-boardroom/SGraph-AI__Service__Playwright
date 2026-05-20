# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: pilot tests for Screen 4 (Slug detail)
# Drives the real Textual app with an in-memory Local source over a temp stack — no
# mocks. Verifies initial focus, ↑/↓ switch the focused slug (by name, with clamp),
# refresh keeps focus, q quits. @skipUnless textual; screen imported lazily.
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
class test_SG_Edge__TUI__Screen__Slug_Detail(TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='sg-edge-tui-s4-')
        stack    = Local__Edge__Stack(state_dir=self.dir)
        stack.setup()
        stack.register('alice')
        stack.register('bob')
        self.source = SG_Edge__TUI__Local_Source(stack=stack)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def screen(self, slug=''):
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Slug_Detail import SG_Edge__TUI__Screen__Slug_Detail
        return SG_Edge__TUI__Screen__Slug_Detail(source=self.source, slug=slug, refresh_seconds=0)

    def test_initial_focus_and_switch(self):
        asyncio.run(self.scenario_focus())

    async def scenario_focus(self):
        app = self.screen(slug='bob')                                                # opened on a specific slug (Topology drill-in)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.focus_name == 'bob'
            await pilot.press('up')                                                  # bob is index 1 → up moves to alice
            assert app.focus_name == 'alice'
            await pilot.press('up')                                                  # clamp
            assert app.focus_name == 'alice'
            await pilot.press('down')
            assert app.focus_name == 'bob'

    def test_default_focus_first(self):
        asyncio.run(self.scenario_default())

    async def scenario_default(self):
        app = self.screen()                                                          # no initial slug → first
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.focus_name == 'alice'
            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True

    def test_refresh_keeps_focus(self):
        asyncio.run(self.scenario_refresh())

    async def scenario_refresh(self):
        app = self.screen(slug='bob')
        async with app.run_test() as pilot:
            await pilot.pause()
            self.source.register('carol')
            await pilot.press('r')
            await pilot.pause()
            assert app.focus_name == 'bob'                                           # focus stable across refresh
            assert 'carol' in {s.slug for s in app.snapshot.slugs}
