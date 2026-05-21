# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — Cli__Firehose
# Drives `firehose ls` / `describe` via CliRunner with the client factory replaced by
# the fake from the client test — no AWS, no mocks.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase, skipUnless

try:
    import typer                                                                     # noqa: F401
    from typer.testing import CliRunner
    HAS_TYPER = True
except Exception:
    HAS_TYPER = False

from sgraph_ai_service_playwright__cli.aws.firehose.tests.test_Firehose__AWS__Client import FakeFirehose


@skipUnless(HAS_TYPER, 'typer not installed')
class test_Cli__Firehose(TestCase):

    def setUp(self):
        from sgraph_ai_service_playwright__cli.aws.firehose.cli import Cli__Firehose as mod
        self.mod    = mod
        self.runner = CliRunner()
        mod._client_factory = lambda region: FakeFirehose()

    def tearDown(self):
        self.mod._client_factory = None

    def test_ls(self):
        result = self.runner.invoke(self.mod.app, ['ls'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'sgraph-send-cf-logs-to-s3-2' in result.output
        assert 's3://745506449035'           in result.output

    def test_ls_json(self):
        result = self.runner.invoke(self.mod.app, ['ls', '--json'], catch_exceptions=False)
        assert result.exit_code == 0
        assert '"destination_bucket"' in result.output

    def test_describe(self):
        result = self.runner.invoke(self.mod.app, ['describe', 'sgraph-send-cf-logs-to-s3-2'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'ACTIVE'          in result.output
        assert 'cloudfront-realtime/' in result.output
