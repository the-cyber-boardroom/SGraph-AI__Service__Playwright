# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Sentinel__Local
# `sg sentinel local *` — the offline full stack. Docker (CF-env sim) is the DEFAULT
# target; pass --direct to run the engine via local node instead.
#
#   sg sentinel local up      [--direct]                  # start the CF-env sim (or check node)
#   sg sentinel local status                              # node / docker / container / sink — what's ready
#   sg sentinel local hit  [METHOD] <path> [--ip IP]      # one request through L1 → L2 → sink (GET assumed)
#   sg sentinel local down                                # stop the container + clear the local sink
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

app     = typer.Typer(name='local', help='Offline full stack (CF-env sim by default, --direct for node): up / status / hit / down.', no_args_is_help=True)
console = Console()


def _sink() -> Local_FS__Log__Sink:
    return Local_FS__Log__Sink(root_dir=default_local_sink_dir())


@app.command('up')
@spec_cli_errors
def cmd_up(direct: bool = typer.Option(False, '--direct', help='Use local node instead of the CF-env sim container.')):
    """Bring up the offline stack — the --docker CF-env sim (default) or --direct node."""
    sink_dir = default_local_sink_dir()
    os.makedirs(sink_dir, exist_ok=True)
    if direct:
        ok = node_available()
        console.print(f"node        : {'[green]found[/green]' if ok else '[red]missing[/red]'}")
        console.print(f'sink (local): {sink_dir}')
        if not ok:
            console.print('[yellow]node not on PATH — drop --direct to use the docker CF-env sim instead.[/yellow]')
            raise typer.Exit(1)
        console.print('[green]local-direct stack ready.[/green]')
        return
    if not docker_available():
        console.print('[red]docker not available (daemon not reachable).[/red] Install/start docker, or use --direct with node.')
        raise typer.Exit(1)
    runtime = Sentinel__Docker__Runtime()
    console.print('Building + starting the CF-env sim container…')
    runtime.up()
    console.print(f'sink (local): {sink_dir}')
    console.print(f'[green]docker CF-env sim ready[/green] at {runtime.base_url()}')


@app.command('status')
@spec_cli_errors
def cmd_status(as_json: bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Show what's ready/running for the local stack (node, docker, container, sink)."""
    sink_dir   = default_local_sink_dir()
    records    = _sink().read_all()
    blocks     = sum(1 for r in records if r.verdict.value == 'block')
    has_docker = docker_available()
    runtime    = Sentinel__Docker__Runtime()
    container  = has_docker and runtime.is_running()
    info = {'node_available'  : node_available(),
            'docker_available': has_docker,
            'container_running': bool(container),
            'container_url'   : runtime.base_url() if container else '',
            'sink_dir'        : sink_dir,
            'records'         : len(records),
            'blocks'          : blocks}
    if as_json:
        typer.echo(json.dumps(info, indent=2)); return

    def flag(ok): return '[green]yes[/green]' if ok else '[red]no[/red]'
    console.print('[bold]SG/Sentinel — local stack[/]')
    console.print(f"  node (direct)     {flag(info['node_available'])}")
    console.print(f"  docker daemon     {flag(info['docker_available'])}")
    console.print(f"  CF-env container  {flag(info['container_running'])}" + (f"  [dim]{info['container_url']}[/dim]" if container else '  [dim](run `up`)[/dim]'))
    console.print(f"  sink              {sink_dir}")
    console.print(f"  records           {info['records']}   ([red]{blocks} block[/red] / [green]{info['records'] - blocks} allow[/green])")
    ready = info['container_running'] or info['node_available']
    console.print(f"  ready to hit      {flag(ready)}" + ('' if ready else '  [dim]run `sg sentinel local up`[/dim]'))


@app.command('hit')
@spec_cli_errors
def cmd_hit(arg1    : str  = typer.Argument(..., metavar='[METHOD] PATH', help='`/path` (GET assumed), or `METHOD /path`.'),
            arg2    : str  = typer.Argument(None, help='Request path, when the first arg is an HTTP method.'),
            ip      : str  = typer.Option('', '--ip', help='Source IP for the synthetic request.'),
            direct  : bool = typer.Option(False, '--direct', help='Use local node instead of the CF-env sim container.'),
            as_json : bool = typer.Option(False, '--json', help='Output as JSON.')):
    """Send one synthetic request through the full L1 → L2 → sink stack (GET assumed)."""
    method, path = ('GET', arg1) if arg2 is None else (arg1, arg2)                   # `hit /etc/passwd` or `hit GET /etc/passwd`
    if direct:
        if not node_available():
            console.print('[red]node not on PATH[/red] — drop --direct to use the docker CF-env sim.')
            raise typer.Exit(1)
        harness = Sentinel__Local__Harness(log_sink=_sink())
    else:
        runtime = Sentinel__Docker__Runtime()
        if not docker_available():
            console.print('[red]docker not available[/red] — start docker, or use --direct with node.')
            raise typer.Exit(1)
        if not runtime.is_running():
            console.print('[yellow]CF-env sim container is not running.[/yellow] Run `sg sentinel local up` first (or use --direct).')
            raise typer.Exit(1)
        harness = Sentinel__Docker__Harness(log_sink=_sink(), runtime=runtime)
    signal, enforce = harness.hit(method, path, source_ip=ip)
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
def cmd_down(keep_logs: bool = typer.Option(False, '--keep-logs', help='Stop the container but keep the local sink.')):
    """Tear down the local stack — stop the CF-env container and clear the local sink."""
    if docker_available():
        Sentinel__Docker__Runtime().down()
        console.print('[green]Stopped[/green] CF-env sim container.')
    if not keep_logs:
        sink_dir = default_local_sink_dir()
        shutil.rmtree(sink_dir, ignore_errors=True)
        console.print(f'[green]Cleared[/green] {sink_dir}')
