# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__SG__Repl --debug behaviour (v0.2.30 / Open-5 Part 1)
#
# Two interaction modes:
#   (A) Inline   — typing `<verb> --debug <args>` in the REPL hoists --debug
#                  to position 0 so the top-level @app.callback() fires.
#   (B) Session  — `debug on` / `debug off` pseudo-commands flip the global
#                  _DEBUG flag in Spec__CLI__Errors for the rest of the REPL.
#
# Both tests use the same plumbing the run loop uses (_extract_debug_flag +
# _handle_debug_toggle), so the assertions stay close to the behaviour and
# don't have to simulate the full input() / Click round-trip.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute.cli.Cli__SG__Repl import (_extract_debug_flag      ,
                                          _handle_debug_toggle     )
import sg_compute.cli.base.Spec__CLI__Errors as errors_module
from   sg_compute.cli.base.Spec__CLI__Errors import set_debug


class test_Cli__SG__Repl__debug(TestCase):

    def test__debug_flag_is_hoisted_to_top_when_typed_at_verb_position(self):
        # User typed `test --debug iam-admin` from the REPL path `aws/credentials`.
        # The full click argv assembled by the run loop is:
        #   ['--debug'] + resolved-path + parts-without-debug
        # Verify the assembled args start with '--debug' and that --debug has
        # been stripped from the verb-level tokens.
        base_path = ['aws', 'credentials']
        parts     = 'test --debug iam-admin'.split()

        debug_present, parts_clean = _extract_debug_flag(parts)

        assert debug_present                     is True
        assert parts_clean                       == ['test', 'iam-admin']     # --debug stripped
        assert '--debug'                         not in parts_clean

        # Mirror the run-loop assembly exactly:
        resolved  = base_path + ['test']                                       # what _resolve would produce
        trailing  = ['iam-admin']
        full_args = (['--debug'] if debug_present else []) + resolved + trailing

        assert full_args[0]                      == '--debug'                  # hoisted to top
        assert full_args                         == ['--debug', 'aws', 'credentials', 'test', 'iam-admin']

    def test__debug_on_pseudo_command_sets_global_debug(self):
        set_debug(False)                                                       # baseline
        assert errors_module._DEBUG              is False

        handled = _handle_debug_toggle(['debug', 'on'])
        assert handled                           is True
        assert errors_module._DEBUG              is True                       # flipped on

        handled = _handle_debug_toggle(['debug', 'off'])
        assert handled                           is True
        assert errors_module._DEBUG              is False                      # flipped off

        # Non-matching shapes are not handled (loop continues to dispatch).
        assert _handle_debug_toggle(['debug'])                  is False
        assert _handle_debug_toggle(['debug', 'maybe'])         is False
        assert _handle_debug_toggle(['something', 'else'])      is False
