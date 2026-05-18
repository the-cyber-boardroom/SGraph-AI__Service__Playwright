# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish setup: Cli__Setup
# Typer app for `sg vault-publish setup` sub-commands.
#
#   sg vault-publish setup iam check    — report vs Waker__Policy__Template
#   sg vault-publish setup iam status   — pretty-print live role config
#   sg vault-publish setup iam create   — create role + policy (mutation-gated)
#   sg vault-publish setup iam update   — sync policy with template (mutation-gated)
#   sg vault-publish setup iam delete   — delete role (delete-gated)
# ═══════════════════════════════════════════════════════════════════════════════

import json
import sys

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute_specs.vault_publish.setup.schemas.Enum__Setup__State import Enum__Setup__State
from sg_compute_specs.vault_publish.setup.service.Setup__IAM         import Setup__IAM

app     = typer.Typer(name='setup', help='Setup and drift-check for vault-publish AWS resources.', no_args_is_help=True)
iam_app = typer.Typer(name='iam',   help='IAM execution role management.',                         no_args_is_help=True)

app.add_typer(iam_app, name='iam')


def _iam() -> Setup__IAM:
    return Setup__IAM()


# ── sg vault-publish setup iam check ─────────────────────────────────────────

@iam_app.command(name='check', help='Check live IAM role vs Waker__Policy__Template.')
def iam_check(output_json: bool = typer.Option(False, '--json', help='Machine-readable JSON output')):
    c    = Console(highlight=False)
    rep  = _iam().check()

    if output_json:
        c.print(json.dumps({
            'state'          : str(rep.state),
            'role_name'      : rep.role_name,
            'role_arn'       : rep.role_arn,
            'role_exists'    : rep.role_exists,
            'policy_name'    : rep.policy_name,
            'policy_matches' : rep.policy_matches,
            'missing_actions': rep.missing_actions,
            'extra_actions'  : rep.extra_actions,
            'issues'         : [{'severity': i.severity, 'area': i.area, 'message': i.message}
                                 for i in rep.issues],
        }, indent=2))
        if rep.state != Enum__Setup__State.OK:
            raise typer.Exit(1)
        return

    _print_iam_report(c, rep)
    if rep.state != Enum__Setup__State.OK:
        raise typer.Exit(1)


# ── sg vault-publish setup iam status ────────────────────────────────────────

@iam_app.command(name='status', help='Pretty-print live IAM role configuration.')
def iam_status():
    c    = Console(highlight=False)
    info = _iam().status()
    c.print()
    for k, v in info.items():
        c.print(f'  {k:<22}: {v}')
    c.print()


# ── sg vault-publish setup iam create ────────────────────────────────────────

@iam_app.command(name='create', help='Create waker IAM role + policy. Requires SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1.')
def iam_create():
    c = Console(highlight=False)
    c.print('\n  [yellow]→[/]  Creating IAM role…')
    try:
        rep = _iam().create()
    except RuntimeError as exc:
        c.print(f'  [red]✗  {exc}[/]')
        raise typer.Exit(1)
    _print_iam_report(c, rep)
    if rep.state == Enum__Setup__State.OK:
        c.print('  [green]✓[/]  IAM role ready')
    c.print()


# ── sg vault-publish setup iam update ────────────────────────────────────────

@iam_app.command(name='update', help='Sync inline policy with Waker__Policy__Template. Requires SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_MUTATIONS=1.')
def iam_update():
    c = Console(highlight=False)
    c.print('\n  [yellow]→[/]  Updating IAM inline policy…')
    try:
        rep = _iam().update()
    except RuntimeError as exc:
        c.print(f'  [red]✗  {exc}[/]')
        raise typer.Exit(1)
    _print_iam_report(c, rep)
    if rep.state == Enum__Setup__State.OK:
        c.print('  [green]✓[/]  Policy updated and matches template')
    c.print()


# ── sg vault-publish setup iam delete ────────────────────────────────────────

@iam_app.command(name='delete', help='Delete waker IAM role. Requires SG_AWS__VAULT_PUBLISH__SETUP__ALLOW_DELETES=1.')
def iam_delete(yes: bool = typer.Option(False, '--yes', '-y', help='Skip confirmation')):
    c = Console(highlight=False)
    if not yes:
        typer.confirm('\n  Delete waker IAM role? This cannot be undone.', default=False, abort=True)
    c.print('\n  [yellow]→[/]  Deleting IAM role…')
    try:
        rep = _iam().delete()
    except RuntimeError as exc:
        c.print(f'  [red]✗  {exc}[/]')
        raise typer.Exit(1)
    c.print('  [green]✓[/]  IAM role deleted')
    c.print()


# ── internal ──────────────────────────────────────────────────────────────────

_STATE_ICON = {
    Enum__Setup__State.OK      : '[green]✓ OK[/]',
    Enum__Setup__State.MISSING : '[red]✗ MISSING[/]',
    Enum__Setup__State.DRIFT   : '[yellow]⚠ DRIFT[/]',
    Enum__Setup__State.ERROR   : '[red]✗ ERROR[/]',
    Enum__Setup__State.UNKNOWN : '[dim]? UNKNOWN[/]',
}


def _print_iam_report(c: Console, rep) -> None:
    c.print()
    icon = _STATE_ICON.get(rep.state, str(rep.state))
    c.print(f'  IAM role: [bold]{rep.role_name}[/]  {icon}')
    if rep.role_arn:
        c.print(f'  ARN     : {rep.role_arn}')
    if rep.missing_actions:
        c.print(f'  [red]Missing actions : {rep.missing_actions}[/]')
    if rep.extra_actions:
        c.print(f'  [yellow]Extra actions   : {rep.extra_actions}[/]')
    for issue in rep.issues:
        sev_colour = {'error': 'red', 'warn': 'yellow', 'info': 'dim'}.get(issue.severity, 'white')
        c.print(f'  [{sev_colour}]{issue.severity.upper()}: {issue.message}[/]')
