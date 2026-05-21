# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: sync render (pure)
# Asserts the plan markup/plain, the complete state, and the post-download result
# line. No textual.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Sync__File   import Schema__CF__Sync__File
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Sync__Plan   import Schema__CF__Sync__Plan
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Sync__Result import Schema__CF__Sync__Result
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Sync__Render import sync_markup, sync_plain


def plan(missing=1):
    p = Schema__CF__Sync__Plan(bucket='b', prefix='cloudfront-realtime/2026/05/21/', date_iso='2026-05-21')
    p.files.append(Schema__CF__Sync__File(key='cloudfront-realtime/2026/05/21/08/a.gz', size=100, present_local=True))
    if missing:
        p.files.append(Schema__CF__Sync__File(key='cloudfront-realtime/2026/05/21/08/b.gz', size=200, present_local=False))
    p.remote_count  = len(p.files)
    p.local_count   = sum(1 for f in p.files if f.present_local)
    p.missing_count = p.remote_count - p.local_count
    return p


class test_sync_markup(TestCase):

    def test_plan(self):
        out = sync_markup(plan())
        for token in ('Sync · raw-cf-logs', '2026-05-21', 'remote', 'missing', 'a.gz', 'b.gz'):
            assert token in out, token

    def test_complete_state(self):
        out = sync_markup(plan(missing=0))
        assert 'complete' in out

    def test_result_line(self):
        res = Schema__CF__Sync__Result(downloaded=2, skipped=1, bytes=300, done=True)
        out = sync_markup(plan(missing=0), result=res)
        assert 'synced 2' in out


class test_sync_plain(TestCase):

    def test_no_markup(self):
        out = sync_plain(plan())
        assert 'Sync · raw-cf-logs' in out
        assert 'missing=1'          in out
        assert '['                  not in out
