# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — smoke tests for scripts/catalog.py typer app
# ═══════════════════════════════════════════════════════════════════════════════

import re
from unittest                                                                       import TestCase

from typer.testing                                                                  import CliRunner


def _plain(text: str) -> str:
    return re.sub(r'\x1b\[[0-9;]*m', '', text)


class test_typer_app(TestCase):

    def setUp(self):
        from scripts.catalog                                                        import app
        self.app    = app
        self.runner = CliRunner()

    def test__exposes_expected_commands(self):
        result   = self.runner.invoke(self.app, ['--help'])
        assert result.exit_code == 0
        out      = _plain(result.stdout)
        for cmd in ('types', 'stacks'):
            assert cmd in out, f'{cmd!r} missing from sp catalog --help'

    def test__stacks_help_shows_type_filter(self):
        result = self.runner.invoke(self.app, ['stacks', '--help'])
        assert result.exit_code == 0
        out    = _plain(result.stdout)
        assert '--type' in out

    def test__stacks_unknown_type_raises_bad_parameter(self):                       # No AWS reached — Enum__Stack__Type rejects in the typer layer
        result = self.runner.invoke(self.app, ['stacks', '--type', 'not-real'])
        assert result.exit_code != 0
        assert "unknown type" in (result.stdout + (result.stderr or ''))
