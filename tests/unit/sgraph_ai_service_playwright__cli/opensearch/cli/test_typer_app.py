# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — smoke tests for scripts/opensearch.py typer app
# Verifies the app exposes the expected commands without invoking AWS.
# Per-command behaviour is covered at the OpenSearch__Service layer.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest                                                                       import TestCase

from typer.testing                                                                  import CliRunner


class test_typer_app(TestCase):

    def setUp(self):
        from scripts.opensearch                                                     import app
        self.app    = app
        self.runner = CliRunner()

    def test__exposes_expected_commands(self):
        result   = self.runner.invoke(self.app, ['--help'])
        assert result.exit_code == 0
        out      = result.stdout
        for cmd in ('create', 'list', 'info', 'delete', 'health'):
            assert cmd in out, f'{cmd!r} missing from sp os --help'

    def test__create_command_help(self):
        result = self.runner.invoke(self.app, ['create', '--help'])
        assert result.exit_code == 0
        assert '--region'        in result.stdout
        assert '--instance-type' in result.stdout
        assert '--password'      in result.stdout

    def test__health_command_help(self):
        result = self.runner.invoke(self.app, ['health', '--help'])
        assert result.exit_code == 0
        assert '--user'     in result.stdout
        assert '--password' in result.stdout
