# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — bedrock tui: applying a loadout to the chat (ctrl+g path)
# A chat launched without tools can be made tool-enabled by applying a loadout (what
# the ctrl+g modal does on Apply). Needs textual; uses the S3 provider (no memory_fs).
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from unittest import TestCase, skipUnless

try:
    import textual                                                                # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

from tests.unit.sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client__In_Memory import S3__AWS__Client__In_Memory

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Engine    import Bedrock__Chat__Engine
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__In_Memory  import Bedrock__Chat__In_Memory
from sgraph_ai_service_playwright__cli.aws.s3.tui_api.S3__Tui_Api__Provider            import S3__Tui_Api__Provider
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Loadout__Assembler import Tui_Api__Loadout__Assembler
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry          import Tui_Api__Registry


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_Bedrock__Chat__Screen__loadout(TestCase):

    def test_apply_loadout_activates_tools(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Screen import Bedrock__Chat__Screen
        screen = Bedrock__Chat__Screen(Bedrock__Chat__Engine(source=Bedrock__Chat__In_Memory()),
                                      region='us-east-1', model_alias='lite')
        async with screen.run_test() as pilot:
            await pilot.pause()
            assert screen.tools_active is False                                   # plain chat → streaming path

            registry = Tui_Api__Registry().register(S3__Tui_Api__Provider(client=S3__AWS__Client__In_Memory()))
            loadout  = Tui_Api__Loadout__Assembler().from_tools('sg-aws.s3:read')
            screen.apply_loadout(registry, loadout)                               # what the ctrl+g modal does on Apply

            assert screen.tools_active is True                                    # now agentic
            assert len(screen.tool_config['tools']) == 3                          # the three read actions reach the model
            assert screen.center is not None
