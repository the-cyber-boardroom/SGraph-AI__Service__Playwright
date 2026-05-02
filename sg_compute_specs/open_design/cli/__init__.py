# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Open Design CLI
# Typer app: sp open-design create / list / info / delete / health / wait
# Tier-2A pattern: thin wrapper — logic lives in Open_Design__Service.
# ═══════════════════════════════════════════════════════════════════════════════

import functools
import traceback
import webbrowser
from typing import Optional

import typer
from rich.console import Console

from sg_compute_specs.open_design.cli.Renderers                                 import (render_create ,
                                                                                              render_delete ,
                                                                                              render_info   ,
                                                                                              render_list   )
from sg_compute_specs.open_design.schemas.Schema__Open_Design__Create__Request  import Schema__Open_Design__Create__Request
from sg_compute_specs.open_design.service.Open_Design__Service                  import Open_Design__Service, DEFAULT_REGION

app = typer.Typer(no_args_is_help=True,
                  help='Manage ephemeral Open Design EC2 stacks',
                  add_completion=False)

DEBUG_TRACE = False


@app.callback()
def _root(debug: bool = typer.Option(False, '--debug',
                                     help='Show full Python traceback on errors.')):
    global DEBUG_TRACE
    DEBUG_TRACE = debug


def _svc() -> Open_Design__Service:
    return Open_Design__Service().setup()


def _err_handler(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except typer.Exit:
            raise
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            c = Console(highlight=False, stderr=True)
            c.print()
            c.print(f'  [red]✗[/]  [bold]{type(exc).__name__}[/]: {exc}')
            if not DEBUG_TRACE:
                c.print('     [dim]› Re-run with [bold]sp open-design --debug ...[/] to see the full traceback.[/]')
            if DEBUG_TRACE:
                c.print()
                c.print('[dim]── traceback ────────────────────────────────────[/]')
                c.print(traceback.format_exc(), end='')
            c.print()
            raise typer.Exit(2)
    return wrapped


def resolve_stack_name(svc: Open_Design__Service, provided: Optional[str], region: str) -> str:
    if provided:
        return provided
    listing      = svc.list_stacks(region)
    names        = [s.stack_name for s in listing.stacks if s.stack_name]
    region_label = listing.region or 'the current region'
    if len(names) == 0:
        Console(highlight=False, stderr=True).print(
            f'\n  [yellow]No open-design stacks in {region_label}.[/]  Run: [bold]sp open-design create[/]\n')
        raise typer.Exit(1)
    if len(names) == 1:
        Console(highlight=False).print(f'\n  [dim]One stack found — using [bold]{names[0]}[/][/]')
        return names[0]
    c = Console(highlight=False)
    c.print(f'\n  [bold]Multiple stacks in {region_label}:[/]')
    for idx, name in enumerate(names, start=1):
        c.print(f'    {idx}. {name}')
    raw = typer.prompt('\n  Pick a stack number', type=int)
    try:
        choice = int(raw)
    except (TypeError, ValueError):
        choice = -1
    if choice < 1 or choice > len(names):
        Console(highlight=False, stderr=True).print(f'\n  [red]Invalid selection: {raw}[/]\n')
        raise typer.Exit(1)
    return names[choice - 1]


@app.command()
@_err_handler
def create(
    name          : Optional[str] = typer.Argument(None, help='Stack name; auto-generated if omitted.'),
    region        : str           = typer.Option(DEFAULT_REGION , '--region'       , '-r', help='AWS region.'                          ),
    instance_type : str           = typer.Option('t3.large'     , '--instance-type', '-t', help='EC2 instance type.'                   ),
    from_ami      : Optional[str] = typer.Option(None           , '--ami'          ,       help='AMI ID; latest AL2023 used if omitted.'),
    caller_ip     : Optional[str] = typer.Option(None           , '--caller-ip'    ,       help='Source IP; auto-detected if omitted.' ),
    api_key       : str           = typer.Option(''             , '--api-key'      , envvar='ANTHROPIC_API_KEY',
                                                                                            help='Anthropic API key.'                   ),
    ollama_ip     : str           = typer.Option(''             , '--ollama-ip'    ,       help='Ollama EC2 private IP.'               ),
    ref           : str           = typer.Option('main'         , '--ref'          ,       help='open-design git ref.'                 ),
    max_hours     : int           = typer.Option(1              , '--max-hours'    ,       help='Auto-terminate after N hours; 0=off.' ),
    fast_boot     : bool          = typer.Option(False          , '--fast-boot'    ,       help='Skip pnpm build (baked AMI).'         ),
    wait          : bool          = typer.Option(False          , '--wait'         ,       help='Block until app is healthy.'          ),
    open_browser  : bool          = typer.Option(False          , '--open'         ,       help='Open viewer URL in browser.'          ),
) -> None:
    """Provision an Open Design EC2 stack."""
    c          = Console(highlight=False, width=200)
    ollama_url = f'http://{ollama_ip}:11434/v1' if ollama_ip else ''
    req = Schema__Open_Design__Create__Request(
        region          = region             ,
        instance_type   = instance_type      ,
        from_ami        = from_ami  or ''    ,
        stack_name      = name      or ''    ,
        caller_ip       = caller_ip or ''    ,
        api_key         = api_key            ,
        ollama_base_url = ollama_url         ,
        open_design_ref = ref                ,
        max_hours       = max_hours          ,
        fast_boot       = fast_boot          ,
    )
    svc  = _svc()
    resp = svc.create_stack(req)
    render_create(resp, c)
    if wait:
        _wait_healthy(svc, resp.stack_info.instance_id, resp.stack_info.stack_name, region, 600, c)
    if open_browser and resp.stack_info.viewer_url:
        webbrowser.open(resp.stack_info.viewer_url)


@app.command(name='list')
@_err_handler
def list_stacks(region: str = typer.Option(DEFAULT_REGION, '--region', '-r')) -> None:
    """List all Open Design stacks in the region."""
    listing = _svc().list_stacks(region)
    render_list(listing, Console(highlight=False, width=200))


@app.command()
@_err_handler
def info(
    name   : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
    region : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
) -> None:
    """Show details for a single Open Design stack."""
    c    = Console(highlight=False, width=200)
    svc  = _svc()
    name = resolve_stack_name(svc, name, region)
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No open-design stack matched {name!r}[/]')
        raise typer.Exit(1)
    render_info(data, c)


@app.command()
@_err_handler
def delete(
    name   : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
    region : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
) -> None:
    """Terminate an Open Design stack."""
    c    = Console(highlight=False, width=200)
    svc  = _svc()
    name = resolve_stack_name(svc, name, region)
    resp = svc.delete_stack(region, name)
    render_delete(name, resp.deleted, c)
    if not resp.deleted:
        raise typer.Exit(1)


@app.command()
@_err_handler
def wait(
    name        : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
    region      : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
    timeout_sec : int           = typer.Option(600, '--timeout', help='Max seconds to wait.'),
) -> None:
    """Block until the Open Design app is healthy (HTTPS reachable)."""
    c    = Console(highlight=False, width=200)
    svc  = _svc()
    name = resolve_stack_name(svc, name, region)
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No open-design stack matched {name!r}[/]')
        raise typer.Exit(1)
    _wait_healthy(svc, data.instance_id, name, region, timeout_sec, c)


@app.command()
@_err_handler
def health(
    name   : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
    region : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
    timeout: int           = typer.Option(600, '--timeout', help='Max wait seconds.'),
) -> None:
    """Poll until the Open Design app is healthy (or timeout)."""
    c    = Console(highlight=False, width=200)
    svc  = _svc()
    name = resolve_stack_name(svc, name, region)
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No open-design stack matched {name!r}[/]')
        raise typer.Exit(1)
    _wait_healthy(svc, data.instance_id, name, region, timeout, c)


def _wait_healthy(svc: Open_Design__Service, instance_id: str, stack_name: str,
                  region: str, timeout_sec: int, c: Console) -> None:
    from sg_compute.helpers.health.Health__Poller      import Health__Poller
    from sg_compute.helpers.health.Health__HTTP__Probe import Health__HTTP__Probe
    from sg_compute.helpers.aws.EC2__Instance__Helper  import EC2__Instance__Helper
    c.print(f'  [dim]Waiting for [bold]{stack_name}[/] to become healthy (timeout {timeout_sec}s)…[/]')
    instance_helper = EC2__Instance__Helper()
    # Phase 1 — wait for EC2 running state
    running = instance_helper.wait_for_running(region, instance_id, timeout_sec=timeout_sec)
    if not running:
        c.print(f'  [red]timed out[/] waiting for instance to start')
        raise typer.Exit(1)
    # Phase 2 — re-fetch to get assigned public IP, then HTTP probe
    data = svc.get_stack_info(region, stack_name)
    if not data or not data.public_ip:
        c.print(f'  [red]instance running but no public IP assigned[/]')
        raise typer.Exit(1)
    poller = Health__Poller(instance=instance_helper, probe=Health__HTTP__Probe())
    ok = poller.wait_healthy(region=region, instance_id=instance_id,
                             public_ip=data.public_ip, timeout_sec=timeout_sec)
    if ok:
        c.print(f'  [green]healthy[/] — {data.viewer_url or stack_name}')
    else:
        c.print(f'  [red]timed out[/] after {timeout_sec}s')
        raise typer.Exit(1)
