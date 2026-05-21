# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — cf tui: `... tui` CLI
# Exercises the traffic command's no-TTY fallback (CliRunner stdout is not a terminal
# → static ASCII card, no textual needed) over the default in-memory fixtures, plus
# the help surface and diagnose. @skipUnless typer (like the other CLI suites).
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase, skipUnless

try:
    import typer                                                                     # noqa: F401
    from typer.testing import CliRunner
    HAS_TYPER = True
except Exception:
    HAS_TYPER = False


@skipUnless(HAS_TYPER, 'typer not installed')
class test_Cli__CF__Tui(TestCase):

    def setUp(self):
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cli import Cli__CF__Tui as mod
        self.mod    = mod
        self.runner = CliRunner()

    def test_traffic__no_tty_falls_back_to_card(self):
        result = self.runner.invoke(self.mod.app, ['traffic'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'CF Traffic Reality' in result.output
        assert '/enhancecp'         in result.output                                 # real fixture data survives into the card

    def test_files__no_tty_lists_dir(self):
        result = self.runner.invoke(self.mod.app, ['files'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'CF Log Files'        in result.output
        assert 'cloudfront-realtime' in result.output                                # default in-memory presents the partition tree

    def test_inspect__no_tty_shows_fields(self):
        result = self.runner.invoke(self.mod.app, ['inspect'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'Field Lineage' in result.output
        assert '/enhancecp'    in result.output                                      # first fixture file, line 0

    def test_sync__no_tty_list_and_download(self):
        import tempfile
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.service.CF__Local__Store import CF__Local__Store
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.service.CF__Logs__Sync   import CF__Logs__Sync
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.tests.test_CF__Logs__Sync import FakeLister, FakeFetcher, PREFIX
        from sgraph_ai_service_playwright__cli.tui.debug.Debug__Event_Log                     import Debug__Event_Log
        with tempfile.TemporaryDirectory() as tmp:
            self.mod._sync_factory = lambda bucket, region: CF__Logs__Sync(
                lister=FakeLister(), fetcher=FakeFetcher(),
                store=CF__Local__Store(root=tmp, src_prefix=PREFIX), debug=Debug__Event_Log())
            try:
                r1 = self.runner.invoke(self.mod.app, ['sync', '--date', '2026-05-21'], catch_exceptions=False)
                assert r1.exit_code == 0
                assert 'Sync · raw-cf-logs' in r1.output
                assert 'missing=3'          in r1.output
                r2 = self.runner.invoke(self.mod.app, ['sync', '--date', '2026-05-21', '--mode', 'download'], catch_exceptions=False)
                assert r2.exit_code == 0
                assert 'downloaded=3' in r2.output
            finally:
                self.mod._sync_factory = None

    def test_cache__no_tty_shows_stats(self):
        import tempfile
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.service.CF__Local__Store import CF__Local__Store
        with tempfile.TemporaryDirectory() as tmp:
            store = CF__Local__Store(root=tmp)
            store.write_key('cloudfront-realtime/2026/05/21/08/a.gz', b'hello')
            self.mod._store_factory = lambda: store
            try:
                result = self.runner.invoke(self.mod.app, ['cache'], catch_exceptions=False)
                assert result.exit_code == 0
                assert 'Local Cache · raw-cf-logs' in result.output
                assert 'files=1'                   in result.output
            finally:
                self.mod._store_factory = None

    def test_architecture__no_tty_shows_wiring(self):
        from sgraph_ai_service_playwright__cli.aws.firehose.tests.test_Firehose__AWS__Client import FakeFirehose
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.source.CF_TUI__Arch_Source import CF_TUI__Arch_Source
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.tests.test_CF_TUI__Arch_Source import FakeCF, FakeLogs, FakeS3
        self.mod._arch_factory = lambda bucket, region: CF_TUI__Arch_Source(
            cf_client=FakeCF(), logs_client=FakeLogs(), s3_client=FakeS3(), firehose_client=FakeFirehose(), bucket='b')
        try:
            result = self.runner.invoke(self.mod.app, ['architecture'], catch_exceptions=False)
            assert result.exit_code == 0
            assert 'CF Deployed Architecture'   in result.output
            assert 'UNVERIFIED'                 in result.output                      # per-distribution rt-log mapping
            assert 'E1ABCDE2FGHIJK'             in result.output
            assert 'sgraph-send-cf-logs-to-s3-2' in result.output                    # Firehose→S3 hop now verified
        finally:
            self.mod._arch_factory = None

    def test_help_lists_commands(self):
        result = self.runner.invoke(self.mod.app, ['--help'])
        assert result.exit_code == 0
        for token in ('traffic', 'files', 'inspect', 'architecture', 'sync', 'cache', 'diagnose'):
            assert token in result.output, token

    def test_diagnose_runs(self):
        result = self.runner.invoke(self.mod.app, ['diagnose'])
        assert result.exit_code == 0
        assert 'TERM' in result.output
