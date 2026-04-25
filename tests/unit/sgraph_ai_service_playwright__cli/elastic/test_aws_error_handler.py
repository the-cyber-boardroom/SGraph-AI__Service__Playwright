# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tests for the aws_error_handler decorator in scripts/elastic.py
# Pins the contract that the decorator wraps every Typer command:
#   - NoCredentialsError / ClientError / ... → typer.Exit(2), friendly stderr
#   - typer.Exit              → propagates (no double handling)
#   - KeyboardInterrupt       → propagates
#   - Unrecognised exception  → re-raises so surprises stay loud
#
# No mocks, no patches — uses the real translator and the real decorator.
# ═══════════════════════════════════════════════════════════════════════════════

from io                                                                             import StringIO
from unittest                                                                       import TestCase

import typer
from botocore.exceptions                                                            import NoCredentialsError, NoRegionError
from rich.console                                                                   import Console

from scripts.elastic                                                                import aws_error_handler


class test_aws_error_handler(TestCase):

    def test_nocredentials__raises_typer_exit_2(self):
        @aws_error_handler
        def fn():
            raise NoCredentialsError()
        try:
            fn()
            assert False, 'expected typer.Exit'
        except typer.Exit as exc:
            assert exc.exit_code == 2

    def test_no_region__raises_typer_exit_2(self):
        @aws_error_handler
        def fn():
            raise NoRegionError()
        try:
            fn()
            assert False, 'expected typer.Exit'
        except typer.Exit as exc:
            assert exc.exit_code == 2

    def test_typer_exit__propagates_unchanged(self):                                # Decorator must not catch typer.Exit (would mask intended exits like cmd_delete's 404 path)
        @aws_error_handler
        def fn():
            raise typer.Exit(7)
        try:
            fn()
            assert False, 'expected typer.Exit'
        except typer.Exit as exc:
            assert exc.exit_code == 7

    def test_keyboard_interrupt__propagates(self):
        @aws_error_handler
        def fn():
            raise KeyboardInterrupt()
        try:
            fn()
            assert False, 'expected KeyboardInterrupt'
        except KeyboardInterrupt:
            pass

    def test_unknown_exception__exits_2_with_compact_summary(self):                 # Translator returns recognised=False → decorator now exits 2 instead of leaking the trace
        @aws_error_handler
        def fn():
            raise RuntimeError('something else')
        try:
            fn()
            assert False, 'expected typer.Exit'
        except typer.Exit as exc:
            assert exc.exit_code == 2

    def test_passes_through_normal_return(self):                                    # Happy path — decorator must not alter successful returns
        @aws_error_handler
        def fn():
            return 'ok'
        assert fn() == 'ok'

    def test_debug_flag__off_by_default(self):                                      # Without --debug, the module-level flag stays False
        import scripts.elastic as elastic_mod
        assert elastic_mod.DEBUG_TRACE is False

    def test_debug_flag__included_in_output_when_enabled(self):                     # When DEBUG_TRACE is on, the trace must appear in the captured stderr
        import io as _io
        import scripts.elastic as elastic_mod
        from rich.console import Console as _Console
        # Capture stderr by swapping the Console class for one that writes to a string buffer
        original_console = _Console
        captured        = _io.StringIO()
        elastic_mod.Console = lambda *a, **kw: original_console(file=captured, force_terminal=False, highlight=False)
        elastic_mod.DEBUG_TRACE = True
        try:
            @aws_error_handler
            def fn():
                raise NoCredentialsError()
            try:
                fn()
            except typer.Exit:
                pass
            output = captured.getvalue()
            assert 'AWS credentials not found' in output                            # Friendly headline still shown
            assert '── traceback'              in output                            # Trace block included because DEBUG was on
            assert 'NoCredentialsError'        in output                            # Real Python type name from traceback.format_exc()
        finally:
            elastic_mod.Console     = original_console
            elastic_mod.DEBUG_TRACE = False                                         # Reset for other tests

    def test_debug_flag__trace_hidden_when_disabled(self):
        import io as _io
        import scripts.elastic as elastic_mod
        from rich.console import Console as _Console
        original_console = _Console
        captured        = _io.StringIO()
        elastic_mod.Console = lambda *a, **kw: original_console(file=captured, force_terminal=False, highlight=False)
        elastic_mod.DEBUG_TRACE = False
        try:
            @aws_error_handler
            def fn():
                raise RuntimeError('boom')
            try:
                fn()
            except typer.Exit:
                pass
            output = captured.getvalue()
            assert 'RuntimeError'   in output                                       # Compact summary shown
            assert 'boom'           in output
            assert '── traceback'   not in output                                   # Trace block NOT shown — that's the whole point
            assert '--debug'        in output                                       # Hint pointing the user at --debug
        finally:
            elastic_mod.Console = original_console
