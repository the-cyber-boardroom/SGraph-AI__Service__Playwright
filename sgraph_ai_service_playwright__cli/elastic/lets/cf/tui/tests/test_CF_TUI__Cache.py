# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: cache stats render + screen
# Pure render asserts (empty + populated) and a Textual pilot over a tmp store
# populated by the fake sync — no AWS, no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
import tempfile
from unittest import TestCase, skipUnless

from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.service.CF__Local__Store import CF__Local__Store
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Local__Stats import Schema__CF__Local__Stats
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Local__Day_Stat import Schema__CF__Local__Day_Stat
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Cache__Render import cache_stats_markup, cache_stats_plain

try:
    import textual                                                                   # noqa: F401
    HAS_TEXTUAL = True
except Exception:
    HAS_TEXTUAL = False


def populated_stats():
    s = Schema__CF__Local__Stats(data_type='raw-cf-logs', base_path='/x', exists=True,
                                 total_files=3, total_bytes=300, day_count=1, hour_count=2,
                                 first_day='2026/05/21', last_day='2026/05/21')
    s.days.append(Schema__CF__Local__Day_Stat(day='2026/05/21', files=3, bytes=300, hours=2))
    return s


class test_cache_render(TestCase):

    def test_empty(self):
        out = cache_stats_markup(Schema__CF__Local__Stats(base_path='/x'))
        assert 'empty' in out

    def test_populated(self):
        out = cache_stats_markup(populated_stats())
        for token in ('Local Cache', '2026/05/21', 'files', 'days', 'hours'):
            assert token in out, token

    def test_plain(self):
        out = cache_stats_plain(populated_stats())
        assert 'files=3' in out
        assert '['       not in out


@skipUnless(HAS_TEXTUAL, 'textual not installed')
class test_CF_TUI__Screen__Cache(TestCase):

    def test_mounts_and_scans(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Screen__Cache import CF_TUI__Screen__Cache
        with tempfile.TemporaryDirectory() as tmp:
            store = CF__Local__Store(root=tmp)
            store.write_key('cloudfront-realtime/2026/05/21/08/a.gz', b'hello')
            app = CF_TUI__Screen__Cache(store=store, refresh_seconds=0)
            async with app.run_test() as pilot:
                await pilot.pause()
                assert any(e.category == 'fs.read' for e in app.debug_log.events)
                await pilot.press('q')
                await pilot.pause()
                assert app.exited is True
