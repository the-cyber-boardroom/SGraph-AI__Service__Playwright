# ═══════════════════════════════════════════════════════════════════════════════
# sg_compute tests — Spec__CLI__Errors
# Verifies the @spec_cli_errors decorator branches: re-raise, creds, generic.
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
import typer
from unittest import TestCase

from sg_compute.cli.base.Spec__CLI__Errors import set_debug, spec_cli_errors


class test_Spec__CLI__Errors(TestCase):

    def tearDown(self):
        set_debug(False)

    def test_typer_exit_is_re_raised_unchanged(self):
        @spec_cli_errors
        def fn():
            raise typer.Exit(3)

        with pytest.raises(typer.Exit) as exc_info:
            fn()
        assert exc_info.value.exit_code == 3

    def test_keyboard_interrupt_is_re_raised_unchanged(self):
        @spec_cli_errors
        def fn():
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            fn()

    def test_credential_error_exits_1(self):
        class NoCredentialsError(Exception):
            pass

        @spec_cli_errors
        def fn():
            raise NoCredentialsError('credentials missing')

        with pytest.raises(typer.Exit) as exc_info:
            fn()
        assert exc_info.value.exit_code == 1

    def test_credential_keyword_in_message_exits_1(self):
        @spec_cli_errors
        def fn():
            raise RuntimeError('unable to locate credential file')

        with pytest.raises(typer.Exit) as exc_info:
            fn()
        assert exc_info.value.exit_code == 1

    def test_generic_exception_exits_2(self):
        @spec_cli_errors
        def fn():
            raise ValueError('something broke')

        with pytest.raises(typer.Exit) as exc_info:
            fn()
        assert exc_info.value.exit_code == 2

    def test_debug_flag_included_in_generic_path(self):
        set_debug(True)

        @spec_cli_errors
        def fn():
            raise ValueError('boom')

        with pytest.raises(typer.Exit) as exc_info:
            fn()
        assert exc_info.value.exit_code == 2
