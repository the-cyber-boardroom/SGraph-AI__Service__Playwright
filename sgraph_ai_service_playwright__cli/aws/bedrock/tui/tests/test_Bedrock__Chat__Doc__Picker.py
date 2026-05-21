# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — bedrock tui: document picker + attach flow (C-D1 UI)
# The ^D picker loads a valid file (dismiss → document) and shows an error for a bad
# one; an attached doc rides the next send and the pending list clears. @skipUnless
# textual; uses local files (no memory_fs, no AWS).
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from unittest import TestCase, skipUnless

try:
    import textual                                                                # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Documents import Bedrock__Chat__Documents
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Engine    import Bedrock__Chat__Engine
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__In_Memory  import Bedrock__Chat__In_Memory


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_Bedrock__Chat__Doc__Picker(TestCase):

    def test_picker_loads_valid_file(self):
        asyncio.run(self.scenario_picker())

    async def scenario_picker(self):
        import tempfile, os
        from textual.app    import App
        from textual.widgets import Input
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Doc__Picker import Bedrock__Chat__Doc__Picker

        path = os.path.join(tempfile.mkdtemp(), 'notes.md')
        open(path, 'w').write('the answer is 42')

        class _Host(App):
            def __init__(self): super().__init__(); self.result = 'UNSET'
            def on_mount(self): self.push_screen(Bedrock__Chat__Doc__Picker(), lambda v: setattr(self, 'result', v))

        host = _Host()
        async with host.run_test() as pilot:
            await pilot.pause()
            host.screen.query_one('#path', Input).value = path
            await pilot.press('enter')
            await pilot.pause()
            assert host.result is not None
            assert host.result.format == 'md'
            assert host.result.name   == 'notes_md'

    def test_attached_doc_rides_the_next_send_then_clears(self):
        asyncio.run(self.scenario_send())

    async def scenario_send(self):
        import tempfile, os
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Screen import Bedrock__Chat__Screen
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.widgets.Chat__Composer import Chat__Composer

        path = os.path.join(tempfile.mkdtemp(), 'doc.txt')
        open(path, 'w').write('hello doc')
        document = Bedrock__Chat__Documents().load(path)

        source = Bedrock__Chat__In_Memory()
        source.scripted = [('read it', 120, 10, 200)]
        screen = Bedrock__Chat__Screen(Bedrock__Chat__Engine(source=source), region='us-east-1', model_alias='lite')
        async with screen.run_test() as pilot:
            await pilot.pause()
            screen.pending_docs.append(document)                                  # what the picker's callback does
            screen.chips().refresh_from(screen.pending_docs)
            assert screen.chips().display is True

            composer = screen.query_one('#composer', Chat__Composer)
            composer.focus()
            composer.text = 'summarise the doc'
            await pilot.press('enter')
            await screen.workers.wait_for_complete()
            await pilot.pause()

            user_content = source.calls[-1][1][-1]['content']                     # the doc block reached the model
            assert any('document' in block for block in user_content)
            assert screen.pending_docs == []                                      # cleared after the send
            assert screen.chips().display is False
