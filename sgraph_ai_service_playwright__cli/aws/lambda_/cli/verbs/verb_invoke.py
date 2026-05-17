# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — verb_invoke
# `sg aws lambda <name> invoke` — synchronous Lambda invocation.
# Async (--type Event) requires SG_AWS__LAMBDA__ALLOW_MUTATIONS=1.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import sys

import click
from rich.console import Console

from sg_compute.cli.base.Spec__CLI__Errors                                          import spec_cli_errors
from sgraph_ai_service_playwright__cli.aws.lambda_.service.Lambda__AWS__Client      import Lambda__AWS__Client

console = Console()


def _mutation_guard_async():
    if not os.environ.get('SG_AWS__LAMBDA__ALLOW_MUTATIONS'):
        console.print('[red]Set SG_AWS__LAMBDA__ALLOW_MUTATIONS=1 to allow async Lambda invocation.[/red]')
        raise SystemExit(1)


@click.command('invoke')
@click.pass_context
@click.option('--payload',      default=None,    help='JSON payload string.')
@click.option('--payload-file', default=None,    help='Path to JSON payload file.')
@click.option('--type',         'invoc_type',    default='RequestResponse',
              type=click.Choice(['RequestResponse', 'Event']),
              help='Invocation type: RequestResponse (sync) or Event (async).')
@click.option('--log',          is_flag=True,    default=False, help='Return last 4KB execution log on stderr.')
@click.option('--output-file',  default=None,    help='Write response payload to file instead of stdout.')
@click.option('--json',         'as_json',        is_flag=True, default=False, help='Output as JSON.')
def cmd_invoke(ctx, payload, payload_file, invoc_type, log, output_file, as_json):
    """Invoke a Lambda function synchronously (or async with --type Event)."""
    fn_name = ctx.obj['function_name']
    is_async = invoc_type == 'Event'
    if is_async:
        _mutation_guard_async()

    raw_payload = b'{}'
    if payload:
        raw_payload = payload.encode('utf-8')
    elif payload_file:
        with open(payload_file, 'rb') as f:
            raw_payload = f.read()
    elif not sys.stdin.isatty():
        raw_payload = sys.stdin.buffer.read()

    log_type = 'Tail' if log else 'None'
    with spec_cli_errors():
        client = Lambda__AWS__Client()
        resp   = client.invoke(fn_name, payload=raw_payload, async_=is_async, log_type=log_type)
        if log and resp.log_tail:
            console.print('[dim]--- execution log ---[/dim]', file=sys.stderr)
            console.print(resp.log_tail, file=sys.stderr)
        if as_json:
            click.echo(json.dumps(resp.json(), indent=2))
            return
        if output_file:
            with open(output_file, 'w') as f:
                f.write(resp.payload)
            console.print(f'[green]Response written to {output_file}[/green]')
            return
        if resp.function_error:
            console.print(f'[red]Function error:[/red] {resp.function_error}')
        click.echo(resp.payload)
