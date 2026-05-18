# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute — Spec__CLI__Errors
# Shared @spec_cli_errors decorator.  Caller toggles --debug for tracebacks.
# Module-level _DEBUG flag is set by the @app.callback() the Builder attaches;
# tests can flip it directly via set_debug().
# ═══════════════════════════════════════════════════════════════════════════════

import functools
import traceback

import typer
from rich.console import Console


_DEBUG = False


def set_debug(value: bool) -> None:
    global _DEBUG
    _DEBUG = bool(value)


def _handle_cli_error(exc: Exception) -> None:
    """Render exc to stderr and raise typer.Exit(2). Never returns."""
    c   = Console(highlight=False, stderr=True)
    msg = str(exc)
    if 'credential' in msg.lower() or type(exc).__name__.endswith('NoCredentialsError'):
        c.print(f'\n  [red]✗[/]  AWS credentials not configured: {exc}\n')
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
