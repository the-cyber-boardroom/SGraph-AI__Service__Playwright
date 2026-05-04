# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — doctor.py
# CLI entry-point: sp doctor
# Global preflight checks. Three subcommands:
#
#   sp doctor                — run all checks (default — no subcommand)
#   sp doctor passrole       — iam:PassRole check (replaces sp ensure-passrole)
#   sp doctor preflight      — AWS account / region / ECR / image presence
#
# Per Q4 default (team/comms/briefs/v0.1.97__clean-top-level-commands/04__open-questions.md):
# scope is preflight (before-create) only. Per-instance health stays in each
# section's own `<section> health` command.
# ═══════════════════════════════════════════════════════════════════════════════

import typer
from rich.console                                                                   import Console

from sgraph_ai_service_playwright__cli.ec2.service.Ec2__AWS__Client                 import (aws_account_id        ,
                                                                                              ensure_caller_passrole,
                                                                                              IAM__ROLE_NAME        )


app = typer.Typer(no_args_is_help=False,                                            # `sp doctor` (no args) runs all checks
                    help='Global preflight checks — AWS account / region / ECR / IAM passrole.')


def _passrole(c: Console) -> bool:
    """Run the iam:PassRole check. Returns True iff the policy is in place."""
    account = aws_account_id()
    result  = ensure_caller_passrole(account)
    if result['ok']:
        action = result['action']
        if action == 'already_exists':
            c.print(f"  [green]✓[/]  {result['detail']}")
        else:
            c.print(f"  [green]✓  Policy created.[/]  {result['detail']}")
            role_arn = f'arn:aws:iam::{account}:role/{IAM__ROLE_NAME}'
            c.print( '  [dim]Policy document:[/]')
            c.print( '  [dim]  Action:    iam:PassRole[/]')
            c.print(f'  [dim]  Resource:  {role_arn}[/]')
            c.print( '  [dim]  Condition: iam:PassedToService = ec2.amazonaws.com[/]')
        return True
    c.print(f"  [yellow]⚠  Skipped.[/]  {result['detail']}")
    role_arn = f'arn:aws:iam::{account}:role/{IAM__ROLE_NAME}'
    c.print( '  Attach this inline policy manually to your IAM user in the AWS console:')
    c.print(f'    Action:    iam:PassRole')
    c.print(f'    Resource:  {role_arn}')
    c.print( '    Condition: iam:PassedToService = ec2.amazonaws.com')
    return False


def _preflight(c: Console) -> bool:
    """AWS account / region / ECR registry resolution. Returns True iff all green."""
    from sgraph_ai_service_playwright__cli.ec2.service.Ec2__AWS__Client             import (aws_region            ,
                                                                                              ecr_registry_host     )
    ok = True
    try:
        account = aws_account_id()
        c.print(f"  [green]✓[/]  AWS account: [bold]{account}[/]")
    except Exception as exc:
        c.print(f"  [red]✗[/]  AWS account lookup failed: {exc}")
        ok = False
    try:
        region = aws_region()
        c.print(f"  [green]✓[/]  AWS region : [bold]{region}[/]")
    except Exception as exc:
        c.print(f"  [red]✗[/]  AWS region lookup failed: {exc}")
        ok = False
    try:
        registry = ecr_registry_host()
        c.print(f"  [green]✓[/]  ECR host   : [bold]{registry}[/]")
    except Exception as exc:
        c.print(f"  [red]✗[/]  ECR registry resolution failed: {exc}")
        ok = False
    return ok


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Run all checks when no subcommand is given."""
    if ctx.invoked_subcommand is not None:
        return
    c = Console(highlight=False, width=200)
    c.print('\n  🩺  [bold]Preflight[/]')
    p_ok = _preflight(c)
    c.print()
    c.print('  🔐  [bold]iam:PassRole[/]')
    r_ok = _passrole(c)
    c.print()
    if not (p_ok and r_ok):
        raise typer.Exit(1)


@app.command()
def passrole():
    """Attach the minimal iam:PassRole inline policy to the current IAM user.

    Required for `sp pw create` to succeed when calling RunInstances with an
    IAM instance profile. The policy is scoped to the playwright-ec2 role
    only, with a condition restricting PassRole to ec2.amazonaws.com — it
    cannot be used to pass the role to Lambda, ECS, or any other service.

    Policy attached: sg-playwright-passrole-ec2 (inline, on the IAM user).
    """
    c = Console(highlight=False, width=200)
    c.print()
    if not _passrole(c):
        c.print()
        raise typer.Exit(1)
    c.print()


@app.command()
def preflight():
    """AWS preflight — verify account / region / ECR access from the current shell."""
    c = Console(highlight=False, width=200)
    c.print()
    if not _preflight(c):
        c.print()
        raise typer.Exit(1)
    c.print()
