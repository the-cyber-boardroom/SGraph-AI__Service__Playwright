# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — smoke tests for scripts/vnc.py typer app
# Verifies the app exposes the expected commands without invoking AWS.
# Per-command behaviour is covered at the Vnc__Service layer.
# ═══════════════════════════════════════════════════════════════════════════════

import re
from unittest                                                                       import TestCase

from typer.testing                                                                  import CliRunner


def _plain(text: str) -> str:                                                       # Strip ANSI escape codes — CI sets FORCE_COLOR=1
    return re.sub(r'\x1b\[[0-9;]*m', '', text)


class test_typer_app(TestCase):

    def setUp(self):
        from scripts.vnc                                                            import app
        self.app    = app
        self.runner = CliRunner()

    def test__exposes_expected_commands(self):
        result   = self.runner.invoke(self.app, ['--help'])
        assert result.exit_code == 0
        out      = _plain(result.stdout)
        for cmd in ('create', 'list', 'info', 'delete', 'health', 'wait', 'flows', 'interceptors'):
            assert cmd in out, f'{cmd!r} missing from sp vnc --help'

    def test__create_command_help_includes_interceptor_and_wait_flags(self):         # N5 + --wait
        result = self.runner.invoke(self.app, ['create', '--help'])
        assert result.exit_code == 0
        out    = _plain(result.stdout)
        assert '--interceptor'        in out
        assert '--interceptor-script' in out
        assert '--wait'               in out                                          # Block until reachable

    def test__root_supports_debug_flag(self):                                         # mirrors sp linux / sp docker_stack pattern
        result = self.runner.invoke(self.app, ['--help'])
        assert result.exit_code == 0
        out    = _plain(result.stdout)
        assert '--debug' in out

    def test__health_command_help(self):
        result = self.runner.invoke(self.app, ['health', '--help'])
        assert result.exit_code == 0
        out    = _plain(result.stdout)
        assert '--user'     in out
        assert '--password' in out

    def test__wait_command_help(self):                                                # New in this slice
        result = self.runner.invoke(self.app, ['wait', '--help'])
        assert result.exit_code == 0
        out    = _plain(result.stdout)
        assert '--timeout' in out
        assert '--poll'    in out

    def test__delete_argument_is_optional(self):                                      # Auto-pick when only one stack exists
        result = self.runner.invoke(self.app, ['delete', '--help'])
        assert result.exit_code == 0
        out    = _plain(result.stdout)
        assert '[NAME]' in out                                                        # Brackets = optional argument

    def test__interceptors_command_lists_baked_examples(self):                      # No service call needed
        result = self.runner.invoke(self.app, ['interceptors'])
        assert result.exit_code == 0
        out    = _plain(result.stdout)
        assert 'header_logger'   in out
        assert 'header_injector' in out
        assert 'flow_recorder'   in out
