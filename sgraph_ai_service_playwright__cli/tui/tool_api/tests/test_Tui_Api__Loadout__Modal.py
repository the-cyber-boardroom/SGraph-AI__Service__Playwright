# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api tests: Tui_Api__Loadout__Modal
# The loadout picker. Pure state logic (cycle/build) tested directly; the interactive
# flow tested headless via a tiny host App + App.run_test(). @skipUnless textual.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from unittest import TestCase, skipUnless

try:
    import textual                                                                # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory

from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider import S3__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry import Tui_Api__Registry


def _registry():
    return Tui_Api__Registry().register(S3__Tui_Api__Provider(client=S3__AWS__Client__In_Memory()))


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_Tui_Api__Loadout__Modal(TestCase):

    def modal(self):
        from sgraph_ai_service_playwright__cli.tui.tool_api.screens.Tui_Api__Loadout__Modal import Tui_Api__Loadout__Modal
        return Tui_Api__Loadout__Modal(_registry())

    def test_cycle_and_build_loadout(self):
        modal = self.modal()
        assert modal.state['sg-aws.s3'] == 'off'
        modal.cycle_current()                                                     # off → read
        assert modal.state['sg-aws.s3'] == 'read'
        loadout = modal.build_loadout()
        assert len(loadout.grants) == 1
        assert str(loadout.grants[0].scope.api)        == 'sg-aws.s3'
        assert str(loadout.grants[0].scope.capability) == 'read'

    def test_off_grants_nothing(self):
        assert self.modal().build_loadout().grants == []

    def test_pilot_space_then_enter_returns_loadout(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        from textual.app import App
        from sgraph_ai_service_playwright__cli.tui.tool_api.screens.Tui_Api__Loadout__Modal import Tui_Api__Loadout__Modal

        class _Host(App):
            def __init__(self, modal):
                super().__init__()
                self._modal = modal
                self.result = 'UNSET'

            def on_mount(self):
                self.push_screen(self._modal, lambda value: setattr(self, 'result', value))

        host = _Host(Tui_Api__Loadout__Modal(_registry()))
        async with host.run_test() as pilot:
            await pilot.pause()
            await pilot.press('space')                                            # sg-aws.s3 off → read
            await pilot.press('enter')                                            # apply
            await pilot.pause()
            assert host.result is not None
            assert len(host.result.grants) == 1
            assert str(host.result.grants[0].scope.capability) == 'read'
