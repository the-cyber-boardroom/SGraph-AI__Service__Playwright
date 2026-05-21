# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — tui components: Tui__App + Debug__Panel
# Pilot test of the reusable base app: a minimal subclass renders a body and writes to
# the shared debug log; assert the panel starts open, `d` toggles it, and the feed
# reflects recorded events. @skipUnless textual.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from unittest import TestCase, skipUnless

try:
    import textual                                                                   # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_Tui__App(TestCase):

    def app(self):
        from sgraph_ai_service_playwright__cli.tui.components.Tui__App     import Tui__App
        from sgraph_ai_service_playwright__cli.tui.components.Debug__Panel import Debug__Panel

        class Demo(Tui__App):
            def populate(self):
                self.log_event('ui', 'populated')
                self.set_body('hello body')

        return Demo, Debug__Panel

    def test_panel_starts_open_and_toggles(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        Demo, Debug__Panel = self.app()
        app = Demo(debug_open=True, refresh_seconds=0)
        async with app.run_test() as pilot:
            await pilot.pause()
            panel = app.query_one('#debug-panel', Debug__Panel)
            assert panel.has_class('-hidden') is False                               # starts open
            assert app.debug_log.count() >= 1                                        # populate() logged

            await pilot.press('d')                                                   # toggle closed
            await pilot.pause()
            assert panel.has_class('-hidden') is True
            assert app.debug_open is False

            await pilot.press('d')                                                   # toggle open
            await pilot.pause()
            assert panel.has_class('-hidden') is False

            await pilot.press('q')
            await pilot.pause()
            assert app.exited is True
