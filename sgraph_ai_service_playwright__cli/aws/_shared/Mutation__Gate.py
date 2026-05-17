# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Mutation__Gate
# @require_mutation_gate(env_var) decorator.  If the env var is not set to '1',
# raises Typer.Exit(1) with a Rich error panel.  Applied to every mutating
# Typer command in the new aws/* surfaces.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import functools

import typer
from rich.console import Console
from rich.panel   import Panel

_console = Console(stderr=True)


def require_mutation_gate(env_var: str):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if os.environ.get(env_var) != '1':
                _console.print(Panel(
                    f'[bold yellow]{env_var}[/bold yellow] must be set to [bold]1[/bold] '
                    f'to allow this mutation.\n\n'
                    f'  [dim]export {env_var}=1[/dim]',
                    title='[red]Mutation gate[/red]',
                    border_style='red',
                ))
                raise typer.Exit(1)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
