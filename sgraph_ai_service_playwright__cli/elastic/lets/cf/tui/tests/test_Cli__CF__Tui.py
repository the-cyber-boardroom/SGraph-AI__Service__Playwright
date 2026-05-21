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

    def test_files__no_tty_lists_files(self):
        result = self.runner.invoke(self.mod.app, ['files'], catch_exceptions=False)
        assert result.exit_code == 0
        assert 'CF Log Files' in result.output
        assert 'fixtures.tsv' in result.output                                       # default in-memory presents one file

    def test_help_lists_commands(self):
        result = self.runner.invoke(self.mod.app, ['--help'])
        assert result.exit_code == 0
        assert 'traffic'  in result.output
        assert 'files'    in result.output
        assert 'diagnose' in result.output

    def test_diagnose_runs(self):
        result = self.runner.invoke(self.mod.app, ['diagnose'])
        assert result.exit_code == 0
        assert 'TERM' in result.output
