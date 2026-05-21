# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: pilot tests for the shared base (help / theme / export)
# Drives a real screen (Deployment) over an in-memory Local source — no mocks — to
# verify the cross-screen polish: ? opens/closes the help overlay, t toggles the
# theme, e copies the snapshot card to the clipboard (OSC-52). @skipUnless textual.
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
class test_SG_Edge__TUI__App__Base(TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='sg-edge-tui-base-')
        stack    = Local__Edge__Stack(state_dir=self.dir)
        stack.setup()
        stack.register('alice')
        self.source = SG_Edge__TUI__Local_Source(stack=stack)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def screen(self):
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Screen__Deployment import SG_Edge__TUI__Screen__Deployment
        return SG_Edge__TUI__Screen__Deployment(source=self.source, refresh_seconds=0)

    def test_help_lines_are_context_aware(self):
        app  = self.screen()
        keys = {k for k, _ in app.help_lines()}
        assert {'r', 'q', 'question_mark', 't', 'e'} <= keys                          # screen-specific + shared, no Textual defaults

    def test_help_overlay_opens_and_closes(self):
        asyncio.run(self.scenario_help())

    async def scenario_help(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert len(app.screen_stack) == 1
            await pilot.press('question_mark')
            await pilot.pause()
            assert len(app.screen_stack) == 2                                         # help modal pushed
            await pilot.press('escape')
            await pilot.pause()
            assert len(app.screen_stack) == 1                                         # dismissed

    def test_theme_toggle(self):
        asyncio.run(self.scenario_theme())

    async def scenario_theme(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.theme == 'textual-dark'                                        # dark default
            await pilot.press('t')
            assert app.theme == 'textual-light'
            await pilot.press('t')
            assert app.theme == 'textual-dark'

    def test_export_copies_card_to_clipboard(self):
        asyncio.run(self.scenario_export())

    async def scenario_export(self):
        app = self.screen()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press('e')
            await pilot.pause()
            assert 'SG/Edge'  in (app.clipboard or '')                                # OSC-52 card copied
            assert 'alice'    in app.clipboard
