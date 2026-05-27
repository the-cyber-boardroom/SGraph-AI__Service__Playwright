# ═══════════════════════════════════════════════════════════════════════════════
# User-Journey — Cli__User_Journey
# Typer umbrella for `sg user-journey` / `sg uj` — the operator's door to the suite
# conductor:
#
#   status    cockpit snapshot of a suite run (worker grid + aggregates)
#   scale     resize a running suite (count + concurrency)
#   stop      stop a running suite
#   cockpit   live Textual cockpit (lazy import — interactive)
#   chat      conversational cockpit; LLM drives via the granted workflow tools (lazy)
#
# status/scale/stop go through Conductor__Client and are CliRunner-tested via the
# module-level _client_factory seam (no HTTP, no mocks). cockpit/chat lazy-import the
# cli-package TUI at call time, so the spec never statically imports the cli package.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os

import typer
from rich.console import Console

app = typer.Typer(name            = 'user-journey',
                  help            = 'User-journey suite conductor — status / scale / stop + cockpit / chat.',
                  no_args_is_help = True)

_client_factory = None                                                              # tests assign callable() → Conductor__Client
_runner_factory = None                                                              # tests assign callable() → Journey__Local__Runner


def _client(conductor: str, api_key: str):
    if _client_factory is not None:
        return _client_factory()
    from sg_compute_specs.user_journey.core.clients.Conductor__Client import Conductor__Client
    base   = conductor or os.environ.get('SG_UJ__CONDUCTOR_URL',     '')
    key    = api_key   or os.environ.get('SG_UJ__CONDUCTOR_API_KEY', '')
    client = Conductor__Client()
    if base: client.base_url = base
    if key:  client.api_key  = key
    return client


@app.command(name='status', help='Cockpit snapshot of a suite run (worker grid + aggregates).')
def status(suite_run_id: str  = typer.Argument(..., help='Suite run id.'),
           conductor   : str  = typer.Option('', '--conductor', envvar='SG_UJ__CONDUCTOR_URL',     help='Conductor base URL.'),
           api_key     : str  = typer.Option('', '--api-key',   envvar='SG_UJ__CONDUCTOR_API_KEY', help='X-API-Key.'),
           output_json : bool = typer.Option(False, '--json', help='Machine-readable JSON output.')):
    from sg_compute_specs.user_journey.tui.render.User_Journey__Cockpit__Render import User_Journey__Cockpit__Render
    console = Console(highlight=False)
    try:
        snapshot = _client(conductor, api_key).get_suite(suite_run_id)
    except Exception as exc:
        console.print(f'\n  [red]✗  {exc}[/]\n')
        raise typer.Exit(1)
    if output_json:
        console.print(json.dumps(snapshot.json(), indent=2))
        return
    console.print()
    for line in User_Journey__Cockpit__Render().lines(snapshot):
        console.print(f'  {line}')
    console.print()


@app.command(name='scale', help='Resize a running suite (count + concurrency).')
def scale(suite_run_id: str  = typer.Argument(..., help='Suite run id.'),
          count       : int  = typer.Argument(..., help='Target worker count.'),
          concurrency : int  = typer.Argument(..., help='Max workers in flight.'),
          conductor   : str  = typer.Option('', '--conductor', envvar='SG_UJ__CONDUCTOR_URL',     help='Conductor base URL.'),
          api_key     : str  = typer.Option('', '--api-key',   envvar='SG_UJ__CONDUCTOR_API_KEY', help='X-API-Key.'),
          output_json : bool = typer.Option(False, '--json', help='Machine-readable JSON output.')):
    console = Console(highlight=False)
    try:
        snapshot = _client(conductor, api_key).scale_suite(suite_run_id, count, concurrency)
    except Exception as exc:
        console.print(f'\n  [red]✗  {exc}[/]\n')
        raise typer.Exit(1)
    if output_json:
        console.print(json.dumps(snapshot.json(), indent=2))
        return
    console.print(f'\n  [green]✓[/]  scaled [cyan]{suite_run_id}[/] → count={count} concurrency={concurrency}  '
                  f'state={snapshot.state}\n')


@app.command(name='stop', help='Stop a running suite.')
def stop(suite_run_id: str  = typer.Argument(..., help='Suite run id.'),
         conductor   : str  = typer.Option('', '--conductor', envvar='SG_UJ__CONDUCTOR_URL',     help='Conductor base URL.'),
         api_key     : str  = typer.Option('', '--api-key',   envvar='SG_UJ__CONDUCTOR_API_KEY', help='X-API-Key.'),
         output_json : bool = typer.Option(False, '--json', help='Machine-readable JSON output.')):
    console = Console(highlight=False)
    try:
        snapshot = _client(conductor, api_key).stop_suite(suite_run_id)
    except Exception as exc:
        console.print(f'\n  [red]✗  {exc}[/]\n')
        raise typer.Exit(1)
    if output_json:
        console.print(json.dumps(snapshot.json(), indent=2))
        return
    console.print(f'\n  [yellow]■[/]  stopped [cyan]{suite_run_id}[/]  state={snapshot.state}\n')


def _runner(capture_url: str, capture_api_key: str):
    if _runner_factory is not None:
        return _runner_factory()
    from sg_compute_specs.user_journey.core.worker.Journey__Local__Runner import Journey__Local__Runner
    runner = Journey__Local__Runner()
    if capture_url:     runner.capture_url     = capture_url
    if capture_api_key: runner.capture_api_key = capture_api_key
    return runner


def _print_flows(console, flows):
    for record in flows:
        target = record.get('url') or f"{record.get('host', '')}{record.get('path', '')}"
        console.print(f"  {str(record.get('method', '?')):6} {str(record.get('status', '')):>3}  {target}")


@app.command(name='run-local', help='Run ONE journey from a JSON file against a real local Chromium (+ optional mitmproxy capture) and print the result + flows.')
def run_local(journey_file   : str  = typer.Argument(..., help='Path to a journey JSON file.'),
              proxy          : str  = typer.Option('', '--proxy', envvar='SG_PLAYWRIGHT__DEFAULT_PROXY_URL', help='Browser proxy URL (mitmproxy :8080).'),
              capture_url    : str  = typer.Option('', '--capture-url', envvar='SG_UJ__CAPTURE_URL', help='mitmproxy admin URL for flows (:8000).'),
              capture_api_key: str  = typer.Option('', '--capture-api-key', envvar='SG_UJ__CAPTURE_API_KEY', help='mitmproxy X-API-Key.'),
              run_id         : str  = typer.Option('', '--run-id', help='Override the generated run id.'),
              output_json    : bool = typer.Option(False, '--json', help='Machine-readable JSON output.')):
    console = Console(highlight=False)
    if proxy:
        os.environ['SG_PLAYWRIGHT__DEFAULT_PROXY_URL'] = proxy                       # Browser__Launcher reads this at launch
    try:
        journey, rid, result, flows = _runner(capture_url, capture_api_key).run_file(journey_file, run_id or None)
    except Exception as exc:
        console.print(f'\n  [red]✗  {exc}[/]\n')
        raise typer.Exit(1)
    if output_json:
        console.print(json.dumps({'run_id': rid, 'result': result.json(), 'flows': flows}, indent=2))
        return
    console.print(f'\n  [bold]run {rid}[/]  journey=[cyan]{journey.journey_id}[/]  status=[bold]{result.status}[/]')
    console.print(f'  {len(flows)} flow(s) captured')
    _print_flows(console, flows)
    console.print()


@app.command(name='flows', help='Captured network flows for a suite run (one line per request; --json for full).')
def flows(suite_run_id: str  = typer.Argument(..., help='Suite run id.'),
          conductor   : str  = typer.Option('', '--conductor', envvar='SG_UJ__CONDUCTOR_URL',     help='Conductor base URL.'),
          api_key     : str  = typer.Option('', '--api-key',   envvar='SG_UJ__CONDUCTOR_API_KEY', help='X-API-Key.'),
          output_json : bool = typer.Option(False, '--json', help='Machine-readable JSON output.')):
    console = Console(highlight=False)
    try:
        records = _client(conductor, api_key).get_flows(suite_run_id)
    except Exception as exc:
        console.print(f'\n  [red]✗  {exc}[/]\n')
        raise typer.Exit(1)
    if output_json:
        console.print(json.dumps(records, indent=2))
        return
    console.print(f'\n  [bold]{len(records)} flow(s)[/] for [cyan]{suite_run_id}[/]')
    _print_flows(console, records)
    console.print()


@app.command(name='cockpit', help='Live Textual cockpit for a suite run (interactive).')
def cockpit(suite_run_id: str   = typer.Argument(..., help='Suite run id.'),
            conductor   : str   = typer.Option('', '--conductor', envvar='SG_UJ__CONDUCTOR_URL',     help='Conductor base URL.'),
            api_key     : str   = typer.Option('', '--api-key',   envvar='SG_UJ__CONDUCTOR_API_KEY', help='X-API-Key.'),
            refresh     : float = typer.Option(3.0, '--refresh', help='Poll interval in seconds.')):
    from sgraph_ai_service_playwright__cli.tui.screens.user_journey.User_Journey__Cockpit__Screen import User_Journey__Cockpit__Screen
    client = _client(conductor, api_key)
    User_Journey__Cockpit__Screen(conductor=client, suite_run_id=suite_run_id, refresh_seconds=refresh).run()


@app.command(name='chat', help='Conversational cockpit — the LLM drives the conductor via the granted workflow tools.')
def chat(workflow : str = typer.Option('monitor', '--workflow', '-w', help='monitor | operate | load (tool scope).'),
         conductor: str = typer.Option('', '--conductor', envvar='SG_UJ__CONDUCTOR_URL',     help='Conductor base URL.'),
         api_key  : str = typer.Option('', '--api-key',   envvar='SG_UJ__CONDUCTOR_API_KEY', help='X-API-Key.')):
    from sgraph_ai_service_playwright__cli.tui.screens.user_journey.User_Journey__Chat__Launcher import User_Journey__Chat__Launcher
    User_Journey__Chat__Launcher().launch(workflow=workflow, conductor=_client(conductor, api_key))
