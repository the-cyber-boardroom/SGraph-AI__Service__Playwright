# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — tui/tool_api: explorer pilot
# Drives the real Textual explorer via App.run_test() with the S3 provider over the
# in-memory client — no AWS, no mocks. Mirrors the house pilot pattern (asyncio.run +
# @skipUnless textual). Proves: the action table populates, highlighting shows the
# schema, and Enter/'i' invokes a read action through the execution center.
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
    client = (S3__AWS__Client__In_Memory().add_bucket('demo-bucket')
                                          .add_object('demo-bucket', 'logs/a.txt', b'xx'))
    return Tui_Api__Registry().register(S3__Tui_Api__Provider(client=client))


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_Tui_Api__Explorer(TestCase):

    def app(self):
        from sgraph_ai_service_playwright__cli.tui.tool_api.screens.Tui_Api__Explorer import Tui_Api__Explorer
        return Tui_Api__Explorer(registry=_registry())

    def test_table_populates_and_detail_shows(self):
        asyncio.run(self.scenario_table())

    async def scenario_table(self):
        from textual.widgets import DataTable
        app = self.app()
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.query_one('#actions', DataTable)
            assert table.row_count == 3
            assert app.current == ('sg-aws.s3', 'list_buckets')
            assert 'list_buckets' in app.detail_markup                            # the detail pane was rendered on mount

    def test_invoke_read_action_through_center(self):
        asyncio.run(self.scenario_invoke())

    async def scenario_invoke(self):
        app = self.app()
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press('i')                                                # invoke the highlighted row (list_buckets)
            await pilot.pause()
            assert app.last_result is not None and app.last_result.ok is True
            assert 'demo-bucket' in str(app.last_result.json()['data'])
            assert len(app.center.log) == 1                                       # the invoke was audited
