# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — aws shared auth: AWS__Auth__Guard
# The generic recovery layer. Wrap any sg aws command with @aws_auth_guard(family=…):
# on an AWS auth failure it no longer dumps a botocore traceback — it explains the
# cause and offers options (pick a stored credential and retry in-process, or print the
# exact fix). Non-interactive (piped/CI) prints remediation and exits non-zero. The
# store + chooser are injectable so the whole thing is testable with no AWS and no TTY.
# Transparent assume of the family's least-priv role (P5) plugs in via the same path.
# ═══════════════════════════════════════════════════════════════════════════════

import functools
import os
import sys

from sgraph_ai_service_playwright__cli.aws._shared.auth.AWS__Auth__Classifier import is_auth_error, auth_error_cause

ADMIN_ROLE_ENV = 'SG_AWS__IAM__ADMIN_ROLE'                                            # override the default admin credential name


def _default_store():
    from sgraph_ai_service_playwright__cli.credentials.service.Credentials__Store import Credentials__Store
    from sgraph_ai_service_playwright__cli.osx.keyring.service.Keyring__Mac__OS    import Keyring__Mac__OS
    return Credentials__Store(keyring=Keyring__Mac__OS())


def _set_context_role(role : str) -> None:
    from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context import Sg__Aws__Context
    Sg__Aws__Context.set_global_role(role)


def adopt_admin_role_if_available(admin_role : str, store=None, set_role=None, notify=None) -> str:
    # Admin-by-default for management commands: if no base identity is selected and the
    # admin credential (e.g. 'iam-admin') exists in the keyring, adopt it silently-ish.
    # That credential is the whole point of the privileged role — don't make the operator
    # pick it from a menu every time. Returns the adopted role name ('' if none).
    role = os.environ.get(ADMIN_ROLE_ENV) or admin_role
    if not role:
        return ''
    from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context import Sg__Aws__Context
    if Sg__Aws__Context.get_current_role():                                          # operator already chose one (env / `as <role>`) — respect it
        return ''
    store = store if store is not None else _default_store()
    try:
        exists = store.role_get(role) is not None
    except Exception:
        exists = False
    if not exists:                                                                   # not configured here → fall through to the guard menu
        return ''
    (set_role or _set_context_role)(role)
    (notify  or (lambda r: print(f'[iam] using admin credential: {r}', file=sys.stderr)))(role)
    return role


def remediation_text(family : str, cause : str, roles : list) -> str:
    lines = ['', f'AWS auth failed: {cause}', '']
    if roles:
        lines.append('Stored credentials you can use (run, then re-run the command):')
        for r in roles:
            lines.append(f'  eval $(sg credentials switch {r})')
    else:
        lines.append('No stored credentials found. Add one:')
        lines.append('  sg credentials add <role> <access-key> <secret-key>')
    if family:
        lines.append('')
        lines.append(f'Or provision/assume this family\'s least-privilege role:')
        lines.append(f'  sg el lets cf iam create     # create the {family} role (one-off)')
    lines.append('')
    return '\n'.join(lines)


def interactive_chooser(cause : str, family : str, roles : list):                   # returns ('role', name) | ('fix', None) | ('abort', None)
    print(f'\nAWS auth failed: {cause}\n')
    options = [('role', r) for r in roles]
    for i, (_, r) in enumerate(options, start=1):
        print(f'  {i}) use stored credential: {r}')
    print(f'  f) show how to fix')
    print(f'  q) abort')
    raw = input('choose> ').strip().lower()
    if raw == 'f': return ('fix', None)
    if raw == 'q' or raw == '': return ('abort', None)
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(options):
            return options[idx]
    return ('abort', None)


def run_guarded(fn, family : str = '', store=None, chooser=None):
    try:
        return fn()
    except BaseException as exc:                                                     # noqa: BLE001 — re-raise non-auth below
        if not is_auth_error(exc):
            raise
        store = store if store is not None else _default_store()
        try:
            roles = list(store.role_list())
        except Exception:
            roles = []
        cause = auth_error_cause(exc)

        if chooser is None:                                                          # non-interactive → remediation, no traceback
            print(remediation_text(family, cause, roles))
            raise SystemExit(2)

        kind, value = chooser(cause, family, roles)
        if kind == 'role' and value:
            _set_context_role(value)
            return fn()                                                              # retry once with the chosen credential
        if kind == 'fix':
            print(remediation_text(family, cause, roles))
            raise SystemExit(2)
        raise SystemExit(1)                                                          # abort


def aws_auth_guard(family : str = '', admin_role : str = ''):
    # family      → transparent-assume that family's scoped role for the command duration.
    # admin_role  → management commands (e.g. `iam …`) adopt this base credential by
    #               default when none is selected. Mutually sensible: a family role is
    #               assumed FROM the admin identity. Pass one or the other (or neither).
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            from sgraph_ai_service_playwright__cli.aws._shared.auth import AWS__Auth__Context
            from sgraph_ai_service_playwright__cli.credentials.service.Sg__Aws__Context import Sg__Aws__Context
            chooser  = interactive_chooser if sys.stdin.isatty() and sys.stdout.isatty() else None
            adopted  = adopt_admin_role_if_available(admin_role) if admin_role else ''
            if family:
                AWS__Auth__Context.set_active_family(family)                          # transparent assume of the family's scoped role for the duration
            try:
                return run_guarded(lambda: fn(*args, **kwargs), family=family, chooser=chooser)
            finally:
                if family:
                    AWS__Auth__Context.clear_active_family()
                if adopted:
                    Sg__Aws__Context.clear_global_role()                              # don't leak the adopted admin identity into later commands (REPL/tests)
        return wrapper
    return decorator
