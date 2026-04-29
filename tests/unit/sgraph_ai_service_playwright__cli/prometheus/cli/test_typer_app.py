# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — smoke tests for scripts/prometheus.py typer app
# Verifies the app exposes the expected commands without invoking AWS.
# Per-command behaviour is covered at the Prometheus__Service layer.
# ═══════════════════════════════════════════════════════════════════════════════

import re
from unittest                                                                       import TestCase

from typer.testing                                                                  import CliRunner


def _plain(text: str) -> str:                                                       # Strip ANSI escape codes; CI sets FORCE_COLOR=1 which makes Rich emit them through CliRunner, splitting '--foo' into '-' + '-foo'
    return re.sub(r'\x1b\[[0-9;]*m', '', text)


class test_typer_app(TestCase):

    def setUp(self):
        from scripts.prometheus                                                     import app
        self.app    = app
        self.runner = CliRunner()

    def test__exposes_expected_commands(self):
        result   = self.runner.invoke(self.app, ['--help'])
        assert result.exit_code == 0
        out      = _plain(result.stdout)
        for cmd in ('create', 'list', 'info', 'delete', 'health'):
            assert cmd in out, f'{cmd!r} missing from sp prom --help'

    def test__create_command_help(self):
        result = self.runner.invoke(self.app, ['create', '--help'])
        assert result.exit_code == 0
        out    = _plain(result.stdout)
        assert '--region'        in out
        assert '--instance-type' in out

    def test__health_command_help(self):
        result = self.runner.invoke(self.app, ['health', '--help'])
        assert result.exit_code == 0
        out    = _plain(result.stdout)
        assert '--user'     in out
        assert '--password' in out
