# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — verb_invocations
# `sg aws lambda <name> invocations` — recent invocations via Logs Insights.
# Reproduces the AWS console "Recent invocations" panel (REPORT lines).
# ═══════════════════════════════════════════════════════════════════════════════

import json

import click
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                          import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__Invocations__Reporter import Lambda__Invocations__Reporter

console = Console()


def _fmt_ms(val: str) -> str:
    try:
        ms = float(val)
        return f'{ms:.1f} ms'
    except Exception:
        return val or '—'


def _fmt_mb(val: str) -> str:
    try:
        return f'{int(float(val) / 1000 / 1000)} MB'
    except Exception:
        return val or '—'


@click.command('invocations')
@click.pass_context
@click.option('--since',  default='1h',   help='Time window: "30s","5m","2h","1d" or ISO UTC.')
@click.option('--limit',  default=20,     help='Max rows to return.')
@click.option('--failed', is_flag=True,   default=False, help='Only show failed/timed-out invocations.')
@click.option('--json',   'as_json',      is_flag=True, default=False, help='Output as JSON.')
def cmd_invocations(ctx, since, limit, failed, as_json):
    """Show recent invocations from CloudWatch Logs Insights (REPORT lines)."""
    fn_name  = ctx.obj['function_name']
    reporter = Lambda__Invocations__Reporter()
    with spec_cli_errors():
        result = reporter.report(
            function_name = fn_name,
            since         = since,
            limit         = limit,
            failed_only   = failed,
        )
        if result.status not in ('Complete', 'complete'):
            console.print(f'[yellow]Query status: {result.status}[/yellow]')
            return
        if as_json:
            rows = [r.fields for r in result.rows]
            click.echo(json.dumps(rows, indent=2))
            return
        if not result.rows:
            console.print('[dim]No invocations found in the specified window.[/dim]')
            return
        tbl = Table(title=f'Invocations: {fn_name}')
        tbl.add_column('Timestamp',    style='dim',  no_wrap=True)
        tbl.add_column('RequestId',    style='cyan', no_wrap=True)
        tbl.add_column('Duration',     justify='right')
        tbl.add_column('Billed',       justify='right')
        tbl.add_column('Mem used/set', justify='right')
        tbl.add_column('Init',         justify='right')
        for row in result.rows:
            ts_raw  = row.get('@timestamp', '')
            req_raw = row.get('@requestId', '')
            dur_raw = row.get('@duration', '')
            bill_raw = row.get('@billedDuration', '')
            mem_raw  = row.get('@maxMemoryUsed', '')
            mem_set  = row.get('@memorySize', '')
            init_raw = row.get('@initDuration', '')
            req_short = req_raw[:8] + '…' if len(req_raw) > 8 else req_raw
            mem_cell  = f'{_fmt_mb(mem_raw)} / {_fmt_mb(mem_set)}' if mem_set else _fmt_mb(mem_raw)
            tbl.add_row(
                ts_raw[:23] if ts_raw else '—',
                req_short,
                _fmt_ms(dur_raw),
                _fmt_ms(bill_raw),
                mem_cell,
                _fmt_ms(init_raw) if init_raw else '—',
            )
        console.print(tbl)
