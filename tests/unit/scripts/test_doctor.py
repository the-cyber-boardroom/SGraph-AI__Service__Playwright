# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — smoke tests for scripts/doctor.py typer app
# Verifies the app exposes the expected commands without invoking AWS.
# ═══════════════════════════════════════════════════════════════════════════════

import re
from unittest                                                                       import TestCase

from typer.testing                                                                  import CliRunner


def _plain(text: str) -> str:
    return re.sub(r'\x1b\[[0-9;]*m', '', text)


class test_doctor_typer_app(TestCase):

    def setUp(self):
        from scripts.doctor                                                         import app
        self.app    = app
        self.runner = CliRunner()

    def test__exposes_expected_commands(self):
        result   = self.runner.invoke(self.app, ['--help'])
        assert result.exit_code == 0
        out      = _plain(result.stdout)
        for cmd in ('passrole', 'preflight'):
            assert cmd in out, f'{cmd!r} missing from sp doctor --help'

    def test__passrole_help(self):
        result = self.runner.invoke(self.app, ['passrole', '--help'])
        assert result.exit_code == 0
        out    = _plain(result.stdout)
        assert 'iam:PassRole' in out
        assert 'sp pw create' in out                                                # Help string mentions current command path

    def test__preflight_help(self):
        result = self.runner.invoke(self.app, ['preflight', '--help'])
        assert result.exit_code == 0
        out    = _plain(result.stdout)
        assert 'AWS preflight' in out
