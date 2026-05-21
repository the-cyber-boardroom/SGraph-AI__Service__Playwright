# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — bedrock tui: chat screen pilot
# Drives the real Textual app via App.run_test() with an in-memory engine — no AWS,
# no mocks. Covers the core loop (send → user+assistant bubbles, cost tracked), the
# over-cap confirm modal, the Nova model picker, brief capture (writes a file), clear,
# and export. @skipUnless textual.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import os
import shutil
import tempfile
from unittest import TestCase, skipUnless

try:
    import textual                                                                # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Engine   import Bedrock__Chat__Engine
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.source.Bedrock__Chat__In_Memory import Bedrock__Chat__In_Memory


def engine(scripted):
    src = Bedrock__Chat__In_Memory()
    src.scripted = list(scripted)
    return Bedrock__Chat__Engine(source=src)


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_Bedrock__Chat__Screen(TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='bedrock-chat-tui-')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop('SG_AWS__BEDROCK__MAX_CALL_COST', None)

    def screen(self, scripted):
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Screen import Bedrock__Chat__Screen
        return Bedrock__Chat__Screen(engine(scripted), region='us-east-1', model_alias='lite', brief_dir=self.tmp)

    async def _send(self, app, pilot, text):
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.widgets.Chat__Composer import Chat__Composer
        composer = app.query_one('#composer', Chat__Composer)
        composer.focus()
        composer.text = text
        await pilot.press('enter')
        await app.workers.wait_for_complete()
        await pilot.pause()

    # ── core loop + cost ─────────────────────────────────────────────────────────
    def test_send_creates_bubbles_and_tracks_cost(self):
        asyncio.run(self.scenario_send())

    async def scenario_send(self):
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.widgets.Chat__Bubble import Chat__Bubble
        app = self.screen([('the wildcard is not resolving alice', 80, 40, 300)])
        async with app.run_test() as pilot:
            await pilot.pause()
            await self._send(app, pilot, 'why is alice dormant?')

            bubbles = app.query(Chat__Bubble)
            assert len(bubbles) == 2
            assistant = [b for b in bubbles if b.role == 'assistant'][0]
            assert 'wildcard is not resolving alice' in assistant.body_text()

            assert app.session.turn_count    == 1
            assert app.session.total_cost_usd  > 0
            assert app.last_turn.input_tokens  == 80
            assert app.last_turn.output_tokens == 40

    # ── over-cap confirm ───────────────────────────────────────────────────────────
    def test_over_cap_shows_confirm_then_proceeds(self):
        asyncio.run(self.scenario_over_cap())

    async def scenario_over_cap(self):
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Cost__Confirm import Bedrock__Chat__Cost__Confirm
        os.environ['SG_AWS__BEDROCK__MAX_CALL_COST'] = '0.0'                       # any cost trips the cap
        app = self.screen([('ok', 10, 10, 10)])
        async with app.run_test() as pilot:
            await pilot.pause()
            from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.widgets.Chat__Composer import Chat__Composer
            composer = app.query_one('#composer', Chat__Composer)
            composer.focus(); composer.text = 'hello'
            await pilot.press('enter')
            await pilot.pause()
            assert isinstance(app.screen, Bedrock__Chat__Cost__Confirm)            # confirm modal pushed, nothing sent yet
            assert app.session.turn_count == 0

            await pilot.press('y')                                                # confirm → proceed with override
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert app.session.turn_count == 1

    # ── model picker (Nova) ──────────────────────────────────────────────────────
    def test_model_picker_changes_alias(self):
        asyncio.run(self.scenario_picker())

    async def scenario_picker(self):
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Model__Picker import Bedrock__Chat__Model__Picker
        app = self.screen([('ok', 5, 5, 5)])
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press('ctrl+o')
            await pilot.pause()
            picker = app.screen
            assert isinstance(picker, Bedrock__Chat__Model__Picker)
            aliases = [r[0] for r in picker.rows]
            assert aliases == ['default', 'lite', 'micro', 'pro', 'premier']       # Nova only
            # move to 'pro' and select
            target = aliases.index('pro')
            while picker.selected < target:
                await pilot.press('down')
            await pilot.press('enter')
            await pilot.pause()
            assert str(app.session.model_alias) == 'pro'

    # ── brief capture writes a file ───────────────────────────────────────────────
    def test_brief_capture_writes_file(self):
        asyncio.run(self.scenario_brief())

    async def scenario_brief(self):
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Brief__Modal import Bedrock__Chat__Brief__Modal
        app = self.screen([('the wildcard is not resolving alice', 80, 40, 300)])
        async with app.run_test() as pilot:
            await pilot.pause()
            await self._send(app, pilot, 'why is alice dormant?')
            await pilot.press('ctrl+b')
            await pilot.pause()
            assert isinstance(app.screen, Bedrock__Chat__Brief__Modal)
            await pilot.press('w')                                                # write the brief
            await pilot.pause()
            written = list(__import__('pathlib').Path(self.tmp).glob('brief-*.md'))
            assert len(written) == 1
            text = written[0].read_text()
            assert 'Dev brief' in text and 'why is alice dormant?' in text

    # ── clear resets the session ────────────────────────────────────────────────
    def test_clear_resets(self):
        asyncio.run(self.scenario_clear())

    async def scenario_clear(self):
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.widgets.Chat__Bubble import Chat__Bubble
        app = self.screen([('ok one', 10, 10, 10)])
        async with app.run_test() as pilot:
            await pilot.pause()
            await self._send(app, pilot, 'hello')
            assert app.session.turn_count == 1
            await pilot.press('ctrl+l')
            await pilot.pause()
            assert app.session.turn_count   == 0
            assert app.session.total_cost_usd == 0
            assert len(app.query(Chat__Bubble)) == 0
