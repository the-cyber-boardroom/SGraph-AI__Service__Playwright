# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — verb_logs
# `sg aws lambda <name> logs` — CloudWatch Logs events.
# Supports --since, --until, --filter, --stream, --tail, --limit, --json.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import signal
import sys
import time

import click
from rich.console import Console

from sg_compute.cli.base.Spec__CLI__Errors                                          import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client           import Logs__AWS__Client
from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__Time__Parser          import Logs__Time__Parser

console = Console(highlight=False)

_LEVEL_COLORS = {
    'ERROR'   : 'red',
    'Runtime' : 'red',
    'WARNING' : 'yellow',
    'WARN'    : 'yellow',
}


def _color_for(message: str) -> str:
    for key, color in _LEVEL_COLORS.items():
        if key in message:
            return color
    return 'white'


def _fmt_ts(ts_ms: int) -> str:
    import datetime
    dt = datetime.datetime.fromtimestamp(ts_ms / 1000, tz=datetime.timezone.utc)
    return dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # ms precision


@click.command('logs')
@click.pass_context
@click.option('--since',         default=None,  help='Start time: "30s","5m","2h","1d" or ISO UTC.')
@click.option('--until',         default=None,  help='End time (same format as --since).')
@click.option('--filter',        'filter_pat',  default='', help='CloudWatch filter pattern.')
@click.option('--stream',        default=None,  help='Focus on a single log stream prefix.')
@click.option('--tail',          is_flag=True,  default=False, help='Poll for new events (Ctrl-C to stop).')
@click.option('--limit',         default=100,   help='Max events to fetch (non-tail mode).')
@click.option('--poll-interval', default=2000,  help='Poll interval ms (tail mode only).')
@click.option('--json',          'as_json',     is_flag=True, default=False, help='Output as JSON.')
def cmd_logs(ctx, since, until, filter_pat, stream, tail, limit, poll_interval, as_json):
    """Stream or fetch CloudWatch Logs for a Lambda function."""
    fn_name   = ctx.obj['function_name']
    log_group = f'/aws/lambda/{fn_name}'
    tp        = Logs__Time__Parser()

    if tail:
        _tail_mode(log_group, filter_pat, poll_interval)
        return

    with spec_cli_errors():
        start_ms = tp.parse_optional(since, 3600 * 1000)                          # default 1h
        end_ms   = tp.parse(until) if until else None
        streams  = [stream] if stream else None
        client   = Logs__AWS__Client()
        resp     = client.filter_events(
            log_group      = log_group,
            start_time     = start_ms,
            end_time       = end_ms,
            filter_pattern = filter_pat,
            log_streams    = streams,
            limit          = limit,
        )
        if as_json:
            rows = [{'ts': e.timestamp, 'stream': str(e.log_stream),
                     'message': e.message} for e in resp.events]
            click.echo(json.dumps(rows, indent=2))
            return
        if not resp.events:
            console.print('[dim]No log events found for the specified range.[/dim]')
            return
        for ev in resp.events:
            color = _color_for(ev.message)
            console.print(
                f'[dim]{_fmt_ts(ev.timestamp)}[/dim]  [{color}]{ev.message.rstrip()}[/{color}]'
            )


def _tail_mode(log_group: str, filter_pat: str, poll_interval_ms: int):
    console.print(f'[bold]→ tailing {log_group}[/bold]  (Ctrl-C to stop)')
    client    = Logs__AWS__Client()
    count     = 0
    start_ts  = time.time()
    seen_ids  = set()
    last_time = int(time.time() * 1000) - 5000

    def _summarise(signum=None, frame=None):
        elapsed = int(time.time() - start_ts)
        m, s    = divmod(elapsed, 60)
        console.print(f'\n[green]✓ tailed for {m}m{s:02d}s, {count} events shown[/green]')
        sys.exit(0)

    signal.signal(signal.SIGINT, _summarise)

    while True:
        resp = client.filter_events(
            log_group      = log_group,
            start_time     = last_time,
            filter_pattern = filter_pat,
            limit          = 100,
        )
        for ev in resp.events:
            if ev.event_id not in seen_ids:
                seen_ids.add(ev.event_id)
                if ev.timestamp > last_time:
                    last_time = ev.timestamp
                color = _color_for(ev.message)
                console.print(
                    f'[dim]{_fmt_ts(ev.timestamp)}[/dim]  [{color}]{ev.message.rstrip()}[/{color}]'
                )
                count += 1
        time.sleep(poll_interval_ms / 1000.0)
