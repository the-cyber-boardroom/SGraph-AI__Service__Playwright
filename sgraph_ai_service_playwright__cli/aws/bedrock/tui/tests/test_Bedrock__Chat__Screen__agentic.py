# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — bedrock tui: tool-enabled chat pilot (C-TL2b)
# Drives the real chat App with the VFS core tool enabled (the chat tool registers it).
# A scripted agentic source has the model call vfs.read then answer; the read runs
# through the execution center against a seeded VFS. Needs textual + memory_fs → runs
# on the 3.12 venv, skips elsewhere. No AWS, no mocks.
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
class test_Bedrock__Chat__Screen__agentic(TestCase):

    def test_tool_enabled_chat_reads_the_vfs(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.tui_api.Bedrock__Tool_Config__Builder import Bedrock__Tool_Config__Builder
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Screen          import Bedrock__Chat__Screen
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.widgets.Chat__Bubble           import Chat__Bubble
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.widgets.Chat__Composer         import Chat__Composer
        from sgraph_ai_service_playwright__cli.aws.creds.service.Creds__Scope__Catalogue              import Creds__Scope__Catalogue
        from sgraph_ai_service_playwright__cli.tui.tool_api.core.vfs.Vfs__Tui_Api__Provider           import Vfs__Tui_Api__Provider
        from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center         import Tui_Api__Execution_Center
        from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Loadout__Assembler       import Tui_Api__Loadout__Assembler
        from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver      import Tui_Api__Privilege__Resolver
        from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry                 import Tui_Api__Registry

        vfs = Vfs__Tui_Api__Provider()
        vfs.dispatch('vfs.write', {'path': 'notes.md', 'content': 'the answer is 42'})   # seed a file to read
        registry  = Tui_Api__Registry().register(vfs)
        resolver  = Tui_Api__Privilege__Resolver(creds_catalogue=Creds__Scope__Catalogue(catalogue_path=tempfile.mkdtemp() + '/s.json'))
        center    = Tui_Api__Execution_Center(registry=registry, resolver=resolver)
        assembler = Tui_Api__Loadout__Assembler()
        builder   = Bedrock__Tool_Config__Builder()
        granted   = assembler.granted_actions(assembler.from_tools('core.vfs:read'), registry, resolver)
        tool_config, name_map = builder.build(granted)

        source = Bedrock__Chat__In_Memory()
        source.scripted_turns = [
            {'stop_reason': 'tool_use',
             'content'    : [{'toolUse': {'toolUseId': 't1', 'name': builder.tool_name('core.vfs', 'vfs.read'),
                                          'input': {'path': 'notes.md'}}}],
             'input_tokens': 100, 'output_tokens': 20, 'latency_ms': 200},
            {'stop_reason': 'end_turn', 'content': [{'text': 'Your note says the answer is 42.'}],
             'input_tokens': 150, 'output_tokens': 30, 'latency_ms': 250},
        ]
        screen = Bedrock__Chat__Screen(Bedrock__Chat__Engine(source=source), region='us-east-1', model_alias='lite',
                                      registry=registry, center=center, tool_config=tool_config, name_map=name_map)

        assert screen.tools_active is True
        async with screen.run_test() as pilot:
            await pilot.pause()
            composer = screen.query_one('#composer', Chat__Composer)
            composer.focus()
            composer.text = 'what does my note say?'
            await pilot.press('enter')
            await screen.workers.wait_for_complete()
            await pilot.pause()

            assistant = [bubble for bubble in screen.query(Chat__Bubble) if bubble.role == 'assistant'][0]
            assert '42' in assistant.body_text()                                  # the model answered from the file content
            assert screen.last_turn.tool_calls  == 1                              # the VFS read happened
            assert screen.last_turn.model_calls == 2
            assert any(str(call.action_ref) == 'vfs.read' for call in center.log) # executed + audited
