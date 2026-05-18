# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Cli__Lab
# Typer CLI surface for `sg aws lab *` commands.
#
# Command tree:
#   sg aws lab list                        — list registered experiments
#   sg aws lab show    <name>              — show experiment metadata (STUBBED)
#   sg aws lab run     <name>              — run experiment (STUBBED until Agent A)
#   sg aws lab runs list                   — list past runs
#   sg aws lab runs show   <run-id>        — show run detail (STUBBED)
#   sg aws lab runs diff   <run-a> <run-b> — diff two runs (STUBBED)
#   sg aws lab sweep                       — tag-driven leak sweep
#   sg aws lab account show                — show STS caller identity
#   sg aws lab account set-expected <id>   — set expected account guard
#   sg aws lab ledger show                 — dump raw ledger
#   sg aws lab ledger replay               — replay teardown (STUBBED)
#   sg aws lab serve                       — start lab HTTP viewer (STUBBED)
#
# Mutations require SG_AWS__LAB__ALLOW_MUTATIONS=1.
# Lab__Source__Adapter is registered lazily in the callback below.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table   import Table
from rich.panel   import Panel

from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate                   import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws.lab.service.experiments.registry         import list_experiments, get_experiment
from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Ledger                  import Lab__Ledger
from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Safety__Account_Guard   import Lab__Safety__Account_Guard
from sgraph_ai_service_playwright__cli.aws.lab.service.Lab__Sweeper                 import Lab__Sweeper
from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__Dispatcher import Lab__Teardown__Dispatcher

lab_app  = typer.Typer(name='lab', help='Lab measurement harness for AWS infrastructure experiments.', no_args_is_help=True)
runs_app = typer.Typer(name='runs', help='Manage past lab runs.')
acct_app = typer.Typer(name='account', help='Account identity guard.')
ldgr_app = typer.Typer(name='ledger', help='Ledger management.')

lab_app.add_typer(runs_app,  name='runs'   )
lab_app.add_typer(acct_app,  name='account')
lab_app.add_typer(ldgr_app,  name='ledger' )

console       = Console()
_MUTATION_ENV = 'SG_AWS__LAB__ALLOW_MUTATIONS'


@lab_app.callback()
def _lab_callback():
    pass                                                                            # source registration is LAZY — called from sg aws lab verbs only


# ── list ──────────────────────────────────────────────────────────────────────

@lab_app.command('list')
def cmd_list(as_json: bool = typer.Option(False, '--json', help='Output JSON.')):
    experiments = list_experiments()
    if not experiments:
        if as_json:
            console.print_json(json.dumps([]))
        else:
            console.print('[dim]no experiments registered yet (P0 ships in agent-A PR)[/dim]')
        return
    if as_json:
        console.print_json(json.dumps(experiments))
        return
    table = Table(title='Lab Experiments', show_header=True, header_style='bold cyan')
    table.add_column('Name')
    table.add_column('Phase')
    table.add_column('Tier')
    table.add_column('Description')
    for exp in experiments:
        table.add_row(exp['name'], exp['phase'], exp['tier'], exp['description'])
    console.print(table)


# ── show ──────────────────────────────────────────────────────────────────────

@lab_app.command('show')
def cmd_show(name: str = typer.Argument(..., help='Experiment name.')):
    cls = get_experiment(name)
    if cls is None:
        console.print(f'[red]Error:[/red] experiment [bold]{name!r}[/bold] not registered.')
        raise typer.Exit(1)
    console.print(Panel(f'[dim]show: pending Agent implementation for {name!r}[/dim]', title='sg aws lab show'))


# ── run ───────────────────────────────────────────────────────────────────────

@lab_app.command('run')
@require_mutation_gate(_MUTATION_ENV)
def cmd_run(name: str = typer.Argument(..., help='Experiment name to run.')):
    cls = get_experiment(name)
    if cls is None:
        console.print(f'[red]Error:[/red] experiment [bold]{name!r}[/bold] not registered.')
        raise typer.Exit(1)
    console.print(Panel(f'[dim]run: pending Agent implementation for {name!r}[/dim]', title='sg aws lab run'))


# ── sweep ─────────────────────────────────────────────────────────────────────

@lab_app.command('sweep')
def cmd_sweep(apply       : bool           = typer.Option(False, '--apply',       help='Delete leaked resources (default: dry run).'),
              older_than  : Optional[str]  = typer.Option(None,  '--older-than',  help='Only sweep resources older than spec (e.g. 1h, 30m, 2d).'),
              as_json     : bool           = typer.Option(False, '--json',         help='Output JSON.')):
    if apply:
        _assert_mutation_gate()
    ledger     = Lab__Ledger()
    ledger.setup()
    dispatcher = Lab__Teardown__Dispatcher()
    dispatcher.setup()
    sweeper    = Lab__Sweeper(ledger=ledger, dispatcher=dispatcher)
    report     = sweeper.sweep(apply=apply, older_than=older_than)

    if as_json:
        console.print_json(json.dumps({
            'scanned': report.scanned,
            'leaked' : report.leaked,
            'deleted': report.deleted,
            'dry_run': report.dry_run,
        }))
        return

    if report.leaked == 0:
        console.print('[green]✓[/green] no leaked resources found.')
        return

    console.print(f'[yellow]Leaked:[/yellow] {report.leaked} / {report.scanned} scanned. '
                  f'{"Deleted: " + str(report.deleted) if apply else "(dry-run — pass --apply to delete)"}')


# ── runs ──────────────────────────────────────────────────────────────────────

@runs_app.command('list')
def cmd_runs_list(as_json: bool = typer.Option(False, '--json', help='Output JSON.')):
    ledger  = Lab__Ledger()
    ledger.setup()
    entries = ledger.all_entries()
    runs    = {}
    for e in entries:
        run_id = str(e.run_id)
        if run_id not in runs:
            runs[run_id] = {'run_id': run_id, 'entries': 0, 'experiment': e.experiment}
        runs[run_id]['entries'] += 1

    if not runs:
        if as_json:
            console.print_json(json.dumps([]))
        else:
            console.print('[dim]no runs found[/dim]')
        return

    if as_json:
        console.print_json(json.dumps(list(runs.values())))
        return

    table = Table(title='Past Lab Runs', show_header=True, header_style='bold cyan')
    table.add_column('Run ID')
    table.add_column('Experiment')
    table.add_column('Entries', justify='right')
    for r in runs.values():
        table.add_row(r['run_id'], r['experiment'], str(r['entries']))
    console.print(table)


@runs_app.command('show')
def cmd_runs_show(run_id: str = typer.Argument(..., help='Run ID.')):
    console.print(Panel(f'[dim]not implemented in foundation — pending Agent implementation[/dim]', title='sg aws lab runs show'))
    raise typer.Exit(1)


@runs_app.command('diff')
def cmd_runs_diff(run_a: str = typer.Argument(..., help='First run ID.'),
                  run_b: str = typer.Argument(..., help='Second run ID.')):
    console.print(Panel('[dim]not implemented in foundation — pending Agent D implementation[/dim]', title='sg aws lab runs diff'))
    raise typer.Exit(1)


# ── account ───────────────────────────────────────────────────────────────────

@acct_app.command('show')
def cmd_account_show(as_json: bool = typer.Option(False, '--json', help='Output JSON.')):
    guard    = Lab__Safety__Account_Guard()
    identity = guard.get_identity()

    if as_json:
        console.print_json(json.dumps({
            'account_id': str(identity.account_id),
            'user_id'   : identity.user_id,
            'arn'       : str(identity.arn),
            'region'    : str(identity.region),
        }))
        return

    table = Table(title='AWS Account Identity', show_header=True, header_style='bold cyan')
    table.add_column('Field')
    table.add_column('Value')
    table.add_row('Account ID', str(identity.account_id) or '[dim](not available — no AWS credentials)[/dim]')
    table.add_row('User ID'   , identity.user_id or '[dim]n/a[/dim]')
    table.add_row('ARN'       , str(identity.arn)        or '[dim]n/a[/dim]')
    table.add_row('Region'    , str(identity.region)     or '[dim]n/a[/dim]')
    console.print(table)


@acct_app.command('set-expected')
@require_mutation_gate(_MUTATION_ENV)
def cmd_account_set_expected(account_id: str = typer.Argument(..., help='Expected AWS account ID.')):
    guard = Lab__Safety__Account_Guard()
    guard.set_expected(account_id)
    console.print(f'[green]✓[/green] Expected account set to [bold]{account_id}[/bold] for this session.')


# ── ledger ────────────────────────────────────────────────────────────────────

@ldgr_app.command('show')
def cmd_ledger_show(as_json: bool = typer.Option(False, '--json', help='Output JSON.')):
    ledger  = Lab__Ledger()
    ledger.setup()
    entries = ledger.all_entries()

    if as_json:
        data = [ledger._entry_to_dict(e) for e in entries]
        console.print_json(json.dumps(data))
        return

    if not entries:
        console.print('[dim]ledger is empty[/dim]')
        return

    table = Table(title='Lab Ledger', show_header=True, header_style='bold cyan')
    table.add_column('Entry ID')
    table.add_column('Run ID')
    table.add_column('Type')
    table.add_column('State')
    table.add_column('Experiment')
    for e in entries:
        table.add_row(str(e.entry_id)[:8], str(e.run_id)[:20], str(e.resource_type.value) if e.resource_type else '', str(e.state.value) if e.state else '', e.experiment)
    console.print(table)


@ldgr_app.command('replay')
def cmd_ledger_replay():
    console.print(Panel('[dim]not implemented in foundation — pending implementation[/dim]', title='sg aws lab ledger replay'))
    raise typer.Exit(1)


# ── serve ─────────────────────────────────────────────────────────────────────

@lab_app.command('serve')
def cmd_serve():
    console.print(Panel('[dim]not implemented in foundation — pending Agent E implementation[/dim]', title='sg aws lab serve'))
    raise typer.Exit(1)


# ── private helpers ───────────────────────────────────────────────────────────

def _assert_mutation_gate() -> None:
    import os
    if os.environ.get(_MUTATION_ENV) != '1':
        console.print(Panel(
            f'[bold yellow]{_MUTATION_ENV}[/bold yellow] must be set to [bold]1[/bold] '
            f'to allow lab mutations.\n\n  [dim]export {_MUTATION_ENV}=1[/dim]',
            title='[red]Mutation gate[/red]',
            border_style='red',
        ))
        raise typer.Exit(1)
