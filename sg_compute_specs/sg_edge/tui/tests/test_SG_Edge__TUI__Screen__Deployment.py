# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: pilot tests for Screen 1 (Deployment Reality)
# Drives the real Textual app via App.run_test() with an in-memory Local source over
# a temp stack — no mocks. Verifies the wiring: mount loads a snapshot, `r` refreshes
# (picks up a newly-registered slug), `q` exits. @skipUnless textual (gated like the
# CLI suites gate on typer); the screen is imported lazily so this module loads on
# 3.11 even without textual. asyncio.run() avoids a pytest-asyncio dependency.
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
class test_SG_Edge__TUI__Screen__Deployment(TestCase):

    def setUp(self):
        self.dir    = tempfile.mkdtemp(prefix='sg-edge-tui-s1-')
        self.source = SG_Edge__TUI__Local_Source(stack=Local__Edge__Stack(state_dir=self.dir))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def screen(self):
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Deployment import SG_Edge__TUI__Screen__Deployment
        return SG_Edge__TUI__Screen__Deployment(source=self.source, refresh_seconds=0)   # 0 → no timer; tests drive refresh

    def test_mounts_and_loads_snapshot(self):
        asyncio.run(self.scenario_mounts())

    async def scenario_mounts(self):
        self.source.setup()
        self.source.register('alice')
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            from textual.widgets import Static
            assert app.snapshot is not None
            assert {s.slug for s in app.snapshot.slugs} == {'alice'}
            assert app.query_one('#body', Static) is not None                        # body mounted + updated

    def test_refresh_key_picks_up_new_slug(self):
        asyncio.run(self.scenario_refresh())

    async def scenario_refresh(self):
        self.source.setup()
        self.source.register('alice')
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert 'bob' not in {s.slug for s in app.snapshot.slugs}
            self.source.register('bob')                                              # mutate behind the screen
            await pilot.press('r')
            await pilot.pause()
            assert 'bob' in {s.slug for s in app.snapshot.slugs}

    def test_quit_key_exits(self):
        asyncio.run(self.scenario_quit())

    async def scenario_quit(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True
