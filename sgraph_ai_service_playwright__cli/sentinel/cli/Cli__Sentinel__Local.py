# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Sentinel__Local
# `sg sentinel local *` — the offline full stack (Target B, local-direct).
#
#   sg sentinel local up                              # check readiness + ensure sink dir
#   sg sentinel local hit <method> <path> [--ip IP]   # drive one request through L1 → L2 → sink
#   sg sentinel local down                            # clear the local sink
#
# Direct mode needs no daemon — `hit` runs the real node L1 engine + Python L2
# per request and writes to the local-FS sink that `logs`/`blocks` read.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import shutil

import typer
from rich.console import Console

from sgraph_ai_service_playwright__cli.sentinel.runtime.layer1.Sentinel__L1__Source      import node_available
from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Docker__Harness  import Sentinel__Docker__Harness
from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Docker__Runtime  import Sentinel__Docker__Runtime, docker_available
from sgraph_ai_service_playwright__cli.sentinel.runtime.local.Sentinel__Local__Harness   import Sentinel__Local__Harness, default_local_sink_dir
from sgraph_ai_service_playwright__cli.sentinel.service.log_sink.Local_FS__Log__Sink      import Local_FS__Log__Sink
from sg_compute.cli.base.Spec__CLI__Errors                                               import spec_cli_errors

app     = typer.Typer(name='local', help='Offline full stack (local-direct or --docker): up / hit / down.', no_args_is_help=True)
console = Console()


def _sink() -> Local_FS__Log__Sink:
    return Local_FS__Log__Sink(root_dir=default_local_sink_dir())


@app.command('up')
@spec_cli_errors
def cmd_up(docker: bool = typer.Option(False, '--docker', help='Bring up the CF-env simulation container (Target C).')):
    """Bring up the offline stack — local-direct (node) or the --docker CF-env sim."""
    sink_dir = default_local_sink_dir()
    os.makedirs(sink_dir, exist_ok=True)
    if docker:
        if not docker_available():
            console.print('[red]docker not available (daemon not reachable).[/red]')
            raise typer.Exit(1)
        runtime = Sentinel__Docker__Runtime()
        console.print('Building + starting the CF-env sim container…')
        runtime.up()
        console.print(f'sink (local): {sink_dir}')
        console.print(f'[green]docker CF-env sim ready[/green] at {runtime.base_url()}')
        return
    ok = node_available()
    console.print(f"node        : {'[green]found[/green]' if ok else '[red]missing[/red]'}")
    console.print(f'sink (local): {sink_dir}')
    if not ok:
        console.print('[yellow]Install node to run the L1 engine offline.[/yellow]')
        raise typer.Exit(1)
    console.print('[green]local-direct stack ready.[/green]')


@app.command('hit')
@spec_cli_errors
def cmd_hit(method  : str  = typer.Argument(..., help='HTTP method, e.g. GET.'),
            path    : str  = typer.Argument(..., help='Request path, e.g. /etc/passwd.'),
            ip      : str  = typer.Option('', '--ip', help='Source IP for the synthetic request.'),
            docker  : bool = typer.Option(False, '--docker', help='Route via the running CF-env sim container (Target C).'),
            as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Send one synthetic request through the full L1 → L2 → sink stack."""
    if docker:
        if not docker_available():
            console.print('[red]docker not available (daemon not reachable).[/red]')
            raise typer.Exit(1)
        harness = Sentinel__Docker__Harness(log_sink=_sink(), runtime=Sentinel__Docker__Runtime())
    else:
        if not node_available():
            console.print('[red]node not found on PATH — cannot run the L1 engine.[/red]')
            raise typer.Exit(1)
        harness = Sentinel__Local__Harness(log_sink=_sink())
    signal, enforce    = harness.hit(method, path, source_ip=ip)
    if as_json:
        typer.echo(json.dumps({'signal': signal.json(), 'enforcement': enforce.json()}, indent=2))
        return
    colour = 'red' if signal.verdict.value == 'block' else 'green'
    console.print(f'request_id : {signal.request_id}')
    console.print(f'verdict    : [{colour}]{signal.verdict.value}[/{colour}]  (rule {signal.rule_id}, {signal.action.value})')
    console.print(f'reason     : {signal.reason}')
    if enforce.pass_to_origin:
        console.print('enforcement: [green]pass to origin[/green]')
    else:
        console.print(f'enforcement: [red]blocked → HTTP {enforce.http_status}[/red]')


@app.command('down')
@spec_cli_errors
def cmd_down(docker: bool = typer.Option(False, '--docker', help='Stop the CF-env simulation container.')):
    """Tear down — stop the --docker container, or clear the local sink (direct)."""
    if docker:
        Sentinel__Docker__Runtime().down()
        console.print('[green]Stopped[/green] CF-env sim container.')
        return
    sink_dir = default_local_sink_dir()
    shutil.rmtree(sink_dir, ignore_errors=True)
    console.print(f'[green]Cleared[/green] {sink_dir}')
