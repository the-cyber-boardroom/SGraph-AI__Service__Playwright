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


def spec_cli_errors(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (typer.Exit, KeyboardInterrupt):
            raise
        except Exception as exc:
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
    return wrapped
