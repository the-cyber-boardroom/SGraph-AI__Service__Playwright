# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI (tests) — aws shared auth: classifier + guard
# No AWS, no TTY. Covers auth-error classification, the non-interactive remediation
# path, the interactive "pick a stored credential and retry in-process" path, and the
# pass-through of non-auth errors.
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sgraph_ai_service_playwright__cli.aws._shared.auth.AWS__Auth__Classifier import is_auth_error, auth_error_cause
from sgraph_ai_service_playwright__cli.aws._shared.auth.AWS__Auth__Guard      import run_guarded, remediation_text


class _NoCredentialsError(Exception):                                                # stand-in with botocore's class name
    pass
_NoCredentialsError.__name__ = 'NoCredentialsError'


class _ClientError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {'Error': {'Code': code}}


class _FakeStore:
    def __init__(self, roles): self._roles = roles
    def role_list(self): return self._roles


class test_classifier(TestCase):

    def test_no_credentials_is_auth(self):
        assert is_auth_error(_NoCredentialsError('Unable to locate credentials')) is True

    def test_access_denied_is_auth(self):
        assert is_auth_error(_ClientError('AccessDenied')) is True
        assert is_auth_error(_ClientError('ExpiredToken')) is True

    def test_other_client_error_not_auth(self):
        assert is_auth_error(_ClientError('NoSuchKey')) is False

    def test_value_error_not_auth(self):
        assert is_auth_error(ValueError('boom')) is False

    def test_cause_includes_code(self):
        assert 'AccessDenied' in auth_error_cause(_ClientError('AccessDenied'))


class test_run_guarded(TestCase):

    def test_success_passes_through(self):
        assert run_guarded(lambda: 'ok', family='el-lets-cf', store=_FakeStore([])) == 'ok'

    def test_non_auth_error_reraised(self):
        with self.assertRaises(ValueError):
            run_guarded(self._raise(ValueError('nope')), family='x', store=_FakeStore([]))

    def test_non_interactive_remediation_exits(self):
        with self.assertRaises(SystemExit) as ctx:
            run_guarded(self._raise(_NoCredentialsError('no creds')), family='el-lets-cf',
                        store=_FakeStore(['dev', 'prod']), chooser=None)
        assert ctx.exception.code == 2

    def test_pick_role_retries_in_process(self):
        calls = {'n': 0}
        def fn():
            calls['n'] += 1
            if calls['n'] == 1:
                raise _NoCredentialsError('no creds')
            return 'recovered'
        chooser = lambda cause, family, roles: ('role', 'dev')
        result  = run_guarded(fn, family='el-lets-cf', store=_FakeStore(['dev']), chooser=chooser)
        assert result      == 'recovered'
        assert calls['n']  == 2                                                       # retried once after setting the role
        from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context import Sg__Aws__Context
        assert Sg__Aws__Context.get_current_role() == 'dev'
        Sg__Aws__Context.clear_global_role()

    def test_abort_exits(self):
        with self.assertRaises(SystemExit):
            run_guarded(self._raise(_NoCredentialsError('x')), family='', store=_FakeStore([]),
                        chooser=lambda c, f, r: ('abort', None))

    def _raise(self, exc):
        def fn():
            raise exc
        return fn


class test_remediation_text(TestCase):

    def test_lists_roles_and_family(self):
        out = remediation_text('el-lets-cf', 'NoCredentialsError: x', ['dev', 'prod'])
        assert 'sg credentials switch dev'  in out
        assert 'sg el lets cf iam create'   in out

    def test_no_roles_suggests_add(self):
        assert 'sg credentials add' in remediation_text('', 'x', [])
