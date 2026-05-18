# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Spec__CLI__Errors
# Shared @spec_cli_errors decorator / context manager.
#
# AWS-aware: botocore ClientError (UnrecognizedClientException, ExpiredToken,
# AccessDenied, ResourceNotFoundException, ThrottlingException), NoCredentialsError,
# InvalidRegionError / NoRegionError, and EndpointConnectionError all render as
# one-line friendly messages with a Try-this hint instead of a stack trace.
#
# Module-level _DEBUG flag is set by the @app.callback() the Builder attaches;
# tests can flip it directly via set_debug(). When _DEBUG is True the full
# traceback is shown after the friendly message.
# ═══════════════════════════════════════════════════════════════════════════════

import functools
import traceback

import typer
from rich.console import Console


_DEBUG = False


def set_debug(value: bool) -> None:
    global _DEBUG
    _DEBUG = bool(value)


# ── AWS-specific error mapping ────────────────────────────────────────────────
# Code → (icon, headline, hint). Hint is None when no actionable suggestion fits.

_AWS_CLIENT_ERROR_MAP = {
    'UnrecognizedClientException' : ('✗', 'AWS credentials invalid or revoked.',     'eval $(sg aws credentials switch <role>)'),
    'InvalidClientTokenId'        : ('✗', 'AWS credentials invalid or revoked.',     'eval $(sg aws credentials switch <role>)'),
    'AuthFailure'                 : ('✗', 'AWS credentials invalid or revoked.',     'eval $(sg aws credentials switch <role>)'),
    'SignatureDoesNotMatch'       : ('✗', 'AWS credential signature mismatch.',      'check that the access key matches the secret key'),
    'ExpiredToken'                : ('✗', 'AWS session token has expired.',          'eval $(sg aws credentials switch <role>) to refresh'),
    'ExpiredTokenException'       : ('✗', 'AWS session token has expired.',          'eval $(sg aws credentials switch <role>) to refresh'),
    'TokenRefreshRequired'        : ('✗', 'AWS session token has expired.',          'eval $(sg aws credentials switch <role>) to refresh'),
    'AccessDenied'                : ('✗', 'Permission denied.',                       None),
    'AccessDeniedException'       : ('✗', 'Permission denied.',                       None),
    'UnauthorizedOperation'       : ('✗', 'Permission denied.',                       None),
    'ResourceNotFoundException'   : ('✗', 'AWS resource not found.',                  None),
    'NoSuchEntity'                : ('✗', 'AWS resource not found.',                  None),
    'NoSuchBucket'                : ('✗', 'S3 bucket not found.',                     None),
    'ThrottlingException'         : ('⚠', 'AWS API throttling — retry in a moment.', None),
    'Throttling'                  : ('⚠', 'AWS API throttling — retry in a moment.', None),
    'RequestLimitExceeded'        : ('⚠', 'AWS API rate limit exceeded.',             None),
    'TooManyRequestsException'    : ('⚠', 'AWS API rate limit exceeded.',             None),
}


def _render_aws_error(c: Console, exc: Exception) -> bool:                       # True when handled with a friendly message
    cls_name = type(exc).__name__

    if cls_name == 'ClientError' and hasattr(exc, 'response'):                   # botocore.exceptions.ClientError
        err  = getattr(exc, 'response', {}).get('Error', {}) or {}
        code = err.get('Code', '') or ''
        msg  = err.get('Message', '') or str(exc)
        op   = getattr(exc, 'operation_name', '')
        mapped = _AWS_CLIENT_ERROR_MAP.get(code)
        if mapped is not None:
            icon, headline, hint = mapped
            colour = 'yellow' if icon == '⚠' else 'red'
            c.print(f'\n  [{colour}]{icon}[/]  {headline}')
            c.print(f'     [dim]AWS {code}[/]{f" on {op}" if op else ""}: {msg}')
            if hint:
                c.print(f'     [yellow]Try:[/] {hint}')
            c.print()
            return True
        c.print(f'\n  [red]✗[/]  AWS API error.')                                # generic ClientError fallback (still pretty)
        c.print(f'     [dim]{code or cls_name}[/]{f" on {op}" if op else ""}: {msg}')
        c.print()
        return True

    if cls_name == 'NoCredentialsError':
        c.print('\n  [red]✗[/]  No AWS credentials configured.')
        c.print('     [yellow]Try:[/] eval $(sg aws credentials switch <role>)')
        c.print()
        return True

    if cls_name in ('InvalidRegionError', 'NoRegionError'):
        c.print(f'\n  [red]✗[/]  AWS region problem: {exc}')
        c.print('     [yellow]Try:[/] export AWS_DEFAULT_REGION=<region> or pass --region <region>')
        c.print()
        return True

    if cls_name == 'EndpointConnectionError':
        c.print('\n  [red]✗[/]  Cannot reach AWS endpoint (network or region issue).')
        c.print(f'     [dim]{exc}[/]')
        c.print()
        return True

    if cls_name == 'ProfileNotFound':
        c.print(f'\n  [red]✗[/]  AWS profile not found: {exc}')
        c.print('     [yellow]Try:[/] sg aws credentials list')
        c.print()
        return True

    return False


def _handle_cli_error(exc: Exception) -> None:                                   # render exc to stderr and raise typer.Exit; never returns
    c = Console(highlight=False, stderr=True)

    if _render_aws_error(c, exc):
        if _DEBUG:
            c.print('[dim]── traceback ────────────────────────────────────[/]')
            c.print(traceback.format_exc(), end='')
            c.print()
        raise typer.Exit(1)

    msg = str(exc)
    if 'credential' in msg.lower():                                              # keyword fallback for non-botocore credential errors
        c.print(f'\n  [red]✗[/]  AWS credentials problem: {exc}\n')
        raise typer.Exit(1)

    c.print(f'\n  [red]✗[/]  [bold]{type(exc).__name__}[/]: {exc}')
    if _DEBUG:
        c.print('\n[dim]── traceback ────────────────────────────────────[/]')
        c.print(traceback.format_exc(), end='')
    else:
        c.print('     [dim]› Re-run with --debug to see the full traceback.[/]')
    c.print()
    raise typer.Exit(2)


class _Spec__CLI__CM:                                                            # context-manager mode: `with spec_cli_errors():`
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None or issubclass(exc_type, (typer.Exit, KeyboardInterrupt, SystemExit)):
            return False                                                         # don't suppress — let click/typer handle
        _handle_cli_error(exc_val)                                               # always raises typer.Exit; never returns


def spec_cli_errors(fn=None):
    """Dual-mode error handler.

    As a decorator  (@spec_cli_errors): wraps a Typer command function.
    As a CM factory (with spec_cli_errors():): wraps an inline block.
    Both surface exceptions as formatted error messages and raise typer.Exit.
    """
    if fn is not None:                                                           # decorator mode: @spec_cli_errors
        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except (typer.Exit, KeyboardInterrupt):
                raise
            except Exception as exc:
                _handle_cli_error(exc)
        return wrapped
    return _Spec__CLI__CM()                                                      # context manager mode: with spec_cli_errors():
