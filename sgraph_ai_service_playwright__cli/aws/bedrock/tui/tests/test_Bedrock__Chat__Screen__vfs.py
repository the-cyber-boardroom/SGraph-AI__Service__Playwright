# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — bedrock tui: VFS browser panel + clear-preserves-VFS (f3 / ^L)
# F3 opens the VFS browser (sharing the inspector's slot) and shows the session's
# files; ^L clears the conversation but NOT the VFS. Needs textual + memory_fs → 3.12.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import tempfile
from unittest import TestCase, skipUnless

try:
    import textual                                                                # noqa: F401
    import memory_fs                                                              # noqa: F401
    HAS_DEPS = True
except Exception:
    HAS_DEPS = False

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Engine   import Bedrock__Chat__Engine
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__In_Memory import Bedrock__Chat__In_Memory


@skipUnless(HAS_DEPS, 'textual + memory_fs required')
class test_Bedrock__Chat__Screen__vfs(TestCase):

    def _screen_with_vfs(self):
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Screen import Bedrock__Chat__Screen
        from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue     import Creds__Scope__Catalogue
        from sgraph_ai_service_playwright__cli.tui.tool_api.core.vfs.Vfs__Tui_Api__Provider  import Vfs__Tui_Api__Provider
        from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center import Tui_Api__Execution_Center
        from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver import Tui_Api__Privilege__Resolver
        from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry        import Tui_Api__Registry

        vfs = Vfs__Tui_Api__Provider()
        vfs.dispatch('vfs.write', {'path': 'testfile.txt', 'content': 'this is a test file'})
        registry = Tui_Api__Registry().register(vfs)
        resolver = Tui_Api__Privilege__Resolver(creds_catalogue=Creds__Scope__Catalogue(catalogue_path=tempfile.mkdtemp() + '/s.json'))
        center   = Tui_Api__Execution_Center(registry=registry, resolver=resolver)
        return Bedrock__Chat__Screen(Bedrock__Chat__Engine(source=Bedrock__Chat__In_Memory()),
                                    region='eu-west-2', model_alias='lite', registry=registry, center=center)

    def test_f3_browser_shows_files_and_clear_preserves_vfs(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        screen = self._screen_with_vfs()
        async with screen.run_test() as pilot:
            await pilot.pause()
            # default: cost meter shown, inspector + vfs hidden
            assert screen.vfs_browser().display is False and screen.meter().display is True

            await pilot.press('f3'); await pilot.pause()                          # open the VFS browser
            assert screen.vfs_browser().display is True
            assert screen.inspector().display is False and screen.meter().display is False   # shares the slot
            assert 'testfile.txt' in screen._vfs_provider().state()['files']      # the panel is open over the session VFS

            # ^L clears the conversation but must NOT wipe the VFS
            await pilot.press('ctrl+l'); await pilot.pause()
            assert screen.session.turn_count == 0                                 # conversation cleared
            assert screen._vfs_provider().state()['files'] == ['testfile.txt']    # the file survived

            await pilot.press('f3'); await pilot.pause()                          # toggle back to the cost meter
            assert screen.vfs_browser().display is False and screen.meter().display is True
