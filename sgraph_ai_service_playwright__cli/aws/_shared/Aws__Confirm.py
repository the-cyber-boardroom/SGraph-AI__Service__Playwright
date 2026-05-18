# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Aws__Confirm
# Uniform [y/N] prompt + --yes / --dry-run helpers for mutating commands.
# ═══════════════════════════════════════════════════════════════════════════════

import typer
from rich.console import Console

_console = Console()


def confirm_or_abort(message: str, yes: bool = False, dry_run: bool = False) -> bool:
    if dry_run:
        _console.print(f'[dim]Dry-run:[/dim] {message}')
        return False
    if yes:
        return True
    return typer.confirm(message, default=False)
