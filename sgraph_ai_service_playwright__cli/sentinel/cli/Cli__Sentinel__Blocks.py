# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Sentinel__Blocks
# `sg sentinel blocks *` — use case 2 surface. Every block has a logged reason.
#
#   sg sentinel blocks list                    [--json]   # all blocked requests
#   sg sentinel blocks why <request-id|ip>     [--json]   # why a request was blocked
#
# `why <ip>` matches the stored source_ip directly or its hashed form (privacy_mode
# defaults to hash), so an operator can look up by the raw IP they curled with.
# ═══════════════════════════════════════════════════════════════════════════════

import hashlib
import json

import typer
from rich.console import Console
from rich.table   import Table

from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Local__Harness import default_local_sink_dir
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.Local_FS__Log__Sink    import Local_FS__Log__Sink
from sg_compute.cli.base.Spec__CLI__Errors                                             import spec_cli_errors

app     = typer.Typer(name='blocks', help='Inspect blocked requests (list / why).', no_args_is_help=True)
console = Console()


def _sink() -> Local_FS__Log__Sink:
    return Local_FS__Log__Sink(root_dir=default_local_sink_dir())


def _is_block(record) -> bool:
    return record.verdict.value == 'block'


@app.command('list')
@spec_cli_errors
def cmd_list(as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    """List every blocked request and its reason."""
    blocks = [r for r in _sink().read_all() if _is_block(r)]
    if as_json:
        typer.echo(json.dumps([r.json() for r in blocks], indent=2))
        return
    if not blocks:
        console.print('No blocks recorded.')
        return
    t = Table(title='SG/Sentinel — blocks')
    t.add_column('Request', style='cyan')
    t.add_column('Path',    style='bold')
    t.add_column('Rule',    style='yellow')
    t.add_column('HTTP',    justify='right')
    t.add_column('Reason',  style='red')
    for r in blocks:
        t.add_row(str(r.request_id), str(r.path) or '(empty)', str(r.rule_id),
                  str(r.http_status), str(r.reason))
    console.print(t)


@app.command('why')
@spec_cli_errors
def cmd_why(needle  : str  = typer.Argument(..., help='Request id, or the source IP (raw or hashed).'),
            as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Explain why the matching request(s) were blocked."""
    hashed  = hashlib.sha256(needle.encode('utf-8')).hexdigest()[:12]
    matches = [r for r in _sink().read_all()
               if _is_block(r) and (needle == str(r.request_id) or
                                     needle == str(r.source_ip)  or
                                     hashed == str(r.source_ip))]
    if as_json:
        typer.echo(json.dumps([r.json() for r in matches], indent=2))
        return
    if not matches:
        console.print(f'[yellow]No block matches:[/yellow] {needle}')
        raise typer.Exit(1)
    for r in matches:
        console.print(f'[red]blocked[/red] {r.request_id} — rule {r.rule_id} ({r.action.value}, HTTP {r.http_status})')
        console.print(f'   path   : {r.path}')
        console.print(f'   reason : {r.reason}')
