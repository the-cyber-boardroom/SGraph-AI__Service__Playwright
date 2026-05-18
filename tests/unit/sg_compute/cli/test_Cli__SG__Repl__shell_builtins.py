# ═══════════════════════════════════════════════════════════════════════════════
# Tests — Cli__SG__Repl shell builtins (export / unset / cd)
#
# 2026-05-17 user request: support `export SG_AWS__BEDROCK__ALLOW_MUTATIONS=1`
# inside the REPL. subprocess can't help with shell builtins — must be handled
# in-process so the env var persists across subsequent REPL commands.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import tempfile

from unittest import TestCase

from sg_compute.cli.Cli__SG__Repl import _handle_shell_builtin


_GUARD = 'SG_REPL_TEST_GUARD_DO_NOT_USE_IN_PROD'


class test_handle_shell_builtin__export(TestCase):

    def setUp(self):
        os.environ.pop(_GUARD, None)

    def tearDown(self):
        os.environ.pop(_GUARD, None)

    def test__export_sets_env_var(self):
        handled = _handle_shell_builtin(['export', f'{_GUARD}=hello'])
        assert handled is True
        assert os.environ[_GUARD] == 'hello'

    def test__export_overwrites_existing(self):
        os.environ[_GUARD] = 'old'
        _handle_shell_builtin(['export', f'{_GUARD}=new'])
        assert os.environ[_GUARD] == 'new'

    def test__export_accepts_value_with_equals(self):                            # `export X=a=b` should yield X='a=b'
        _handle_shell_builtin(['export', f'{_GUARD}=key=value=other'])
        assert os.environ[_GUARD] == 'key=value=other'

    def test__export_with_bare_var_does_not_unset(self):                         # `export VAR` (no =) just shows the value
        os.environ[_GUARD] = 'still-here'
        _handle_shell_builtin(['export', _GUARD])
        assert os.environ[_GUARD] == 'still-here'

    def test__export_bare_lists_sg_aws_vars(self):                               # `export` with nothing lists SG_*/AWS_*
        handled = _handle_shell_builtin(['export'])
        assert handled is True

    def test__user_reported_case_persists(self):                                 # the exact case from 2026-05-17
        _handle_shell_builtin(['export', 'SG_AWS__BEDROCK__ALLOW_MUTATIONS=1'])
        assert os.environ['SG_AWS__BEDROCK__ALLOW_MUTATIONS'] == '1'
        os.environ.pop('SG_AWS__BEDROCK__ALLOW_MUTATIONS', None)


class test_handle_shell_builtin__unset(TestCase):

    def setUp(self):
        os.environ.pop(_GUARD, None)

    def tearDown(self):
        os.environ.pop(_GUARD, None)

    def test__unset_removes_env_var(self):
        os.environ[_GUARD] = 'value'
        handled = _handle_shell_builtin(['unset', _GUARD])
        assert handled is True
        assert _GUARD not in os.environ

    def test__unset_on_unset_var_is_no_op(self):
        handled = _handle_shell_builtin(['unset', _GUARD])
        assert handled is True
        assert _GUARD not in os.environ

    def test__unset_with_no_args(self):
        handled = _handle_shell_builtin(['unset'])
        assert handled is True


class test_handle_shell_builtin__cd(TestCase):

    def setUp(self):
        self._original_cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._original_cwd)

    def test__cd_changes_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            real_tmp = os.path.realpath(tmp)                                     # macOS /tmp → /private/tmp resolution
            handled = _handle_shell_builtin(['cd', tmp])
            assert handled is True
            assert os.path.realpath(os.getcwd()) == real_tmp

    def test__cd_with_no_args_goes_to_home(self):
        handled = _handle_shell_builtin(['cd'])
        assert handled is True
        assert os.getcwd() == os.path.expanduser('~')

    def test__cd_to_invalid_returns_handled(self):                               # error path: still handled (just prints msg)
        handled = _handle_shell_builtin(['cd', '/path/does/not/exist/anywhere'])
        assert handled is True

    def test__cd_with_tilde_expands(self):
        handled = _handle_shell_builtin(['cd', '~'])
        assert handled is True
        assert os.getcwd() == os.path.expanduser('~')


class test_handle_shell_builtin__non_builtins_passthrough(TestCase):

    def test__non_builtin_returns_false(self):
        assert _handle_shell_builtin(['ls']) is False                            # ls is bash-escaped, not a builtin
        assert _handle_shell_builtin(['nova', 'hello']) is False                  # sg command — not a builtin

    def test__empty_returns_false(self):
        assert _handle_shell_builtin([]) is False
