# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Sentinel__Logs
# `sg sentinel logs *` — use case 1 surface (read the sink).
#
#   sg sentinel logs ls                  [--json]   # every record
#   sg sentinel logs tail [-n N]         [--json]   # last N records
#   sg sentinel logs trace <request-id>  [--json]   # one record (replayable)
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console
from rich.table   import Table

from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Local__Harness import default_local_sink_dir
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.Local_FS__Log__Sink    import Local_FS__Log__Sink
from sg_compute.cli.base.Spec__CLI__Errors                                             import spec_cli_errors

app     = typer.Typer(name='logs', help='Read the log sink (ls / tail / trace).', no_args_is_help=True)
console = Console()


def _sink() -> Local_FS__Log__Sink:
    return Local_FS__Log__Sink(root_dir=default_local_sink_dir())


def _records_table(records, title: str) -> Table:
    t = Table(title=title)
    t.add_column('Received',   style='dim')
    t.add_column('Request',    style='cyan')
    t.add_column('Method')
    t.add_column('Path',       style='bold')
    t.add_column('Verdict',    style='magenta')
    t.add_column('Rule',       style='yellow')
    t.add_column('HTTP',       justify='right')
    for r in records:
        colour = 'red' if r.verdict.value == 'block' else 'green'
        t.add_row(str(r.received_at), str(r.request_id), str(r.method), str(r.path) or '(empty)',
                  f'[{colour}]{r.verdict.value}[/{colour}]', str(r.rule_id),
                  str(r.http_status) if r.http_status else '—')
    return t


@app.command('ls')
@spec_cli_errors
def cmd_ls(as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List every log record in the sink."""
    records = _sink().read_all()
    if as_json:
        typer.echo(json.dumps([r.json() for r in records], indent=2))
        return
    if not records:
        console.print('No log records.')
        return
    console.print(_records_table(records, 'SG/Sentinel — log records'))


@app.command('tail')
@spec_cli_errors
def cmd_tail(lines   : int  = typer.Option(20, '--lines', '-n', help='Number of records to show.'),
             as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show the last N log records."""
    records = list(_sink().read_all())[-lines:]
    if as_json:
        typer.echo(json.dumps([r.json() for r in records], indent=2))
        return
    if not records:
        console.print('No log records.')
        return
    console.print(_records_table(records, f'SG/Sentinel — last {len(records)} records'))


@app.command('trace')
@spec_cli_errors
def cmd_trace(request_id : str  = typer.Argument(..., help='Sentinel request id.'),
              as_json    : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show the full (replayable) record for one request id."""
    record = _sink().get(request_id)
    if record is None:
        console.print(f'[red]No record for request id:[/red] {request_id}')
        raise typer.Exit(1)
    if as_json:
        typer.echo(json.dumps(record.json(), indent=2))
        return
    typer.echo(json.dumps(record.json(), indent=2))
