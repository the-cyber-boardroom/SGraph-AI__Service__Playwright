# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf local cli: native `sp el lets cf sync|cache`
# The canonical, scriptable path. Drives it via CliRunner with the backend factory
# seams replaced by the fake S3 boundaries + a tmp store — no AWS, no mocks. Covers
# list mode, download mode, and the cache stats command + the plain renderers.
# ═══════════════════════════════════════════════════════════════════════════════

import tempfile
from unittest import TestCase, skipUnless

try:
    import typer                                                                     # noqa: F401
    from typer.testing import CliRunner
    HAS_TYPER = True
except Exception:
    HAS_TYPER = False

from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.cli.CF__Local__Render import sync_plain, cache_plain
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Local__Stats import Schema__CF__Local__Stats
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Sync__File   import Schema__CF__Sync__File
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Sync__Plan   import Schema__CF__Sync__Plan


class test_CF__Local__Render(TestCase):

    def test_sync_plain(self):
        p = Schema__CF__Sync__Plan(bucket='b', prefix='cloudfront-realtime/', date_iso='2026-05-21')
        p.files.append(Schema__CF__Sync__File(key='cloudfront-realtime/2026/05/21/08/a.gz', size=100, present_local=True))
        p.remote_count = 1; p.local_count = 1
        out = sync_plain(p)
        assert 'Sync · raw-cf-logs' in out
        assert 'missing=0'          in out
        assert '['                  not in out

    def test_cache_plain_empty(self):
        assert 'empty' in cache_plain(Schema__CF__Local__Stats(base_path='/x'))


@skipUnless(HAS_TYPER, 'typer not installed')
class test_Cli__CF__Local(TestCase):

    def setUp(self):
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.cli import Cli__CF__Local as mod
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.service.CF__Local__Store import CF__Local__Store
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.service.CF__Logs__Sync   import CF__Logs__Sync
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.tests.test_CF__Logs__Sync import FakeLister, FakeFetcher, PREFIX
        from sgraph_ai_service_playwright__cli.tui.debug.Debug__Event_Log                     import Debug__Event_Log
        self.mod    = mod
        self.runner = CliRunner()
        self.tmp    = tempfile.TemporaryDirectory()
        store       = CF__Local__Store(root=self.tmp.name, src_prefix=PREFIX)
        self.store  = store
        mod._sync_factory  = lambda bucket, region: CF__Logs__Sync(lister=FakeLister(), fetcher=FakeFetcher(), store=store, debug=Debug__Event_Log())
        mod._store_factory = lambda: store

    def tearDown(self):
        self.mod._sync_factory  = None
        self.mod._store_factory = None
        self.tmp.cleanup()

    def test_sync_list(self):
        result = self.runner.invoke(self.mod.app, ['sync', '--date', '2026-05-21'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'missing=3' in result.output

    def test_sync_download(self):
        result = self.runner.invoke(self.mod.app, ['sync', '--date', '2026-05-21', '--mode', 'download'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'downloaded=3' in result.output

    def test_cache(self):
        self.runner.invoke(self.mod.app, ['sync', '--date', '2026-05-21', '--mode', 'download'], catch_exceptions=False)
        result = self.runner.invoke(self.mod.app, ['cache'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'files=3' in result.output
