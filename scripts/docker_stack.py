# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — docker_stack.py
# CLI entry-point: sp docker
# Manage ephemeral Docker-on-AL2023 EC2 stacks (Docker CE, SSM access).
#
# Tier-2A thin Typer wrapper — all logic lives in Docker__Service.
# ═══════════════════════════════════════════════════════════════════════════════

import functools
import traceback
from typing                                                                         import List, Optional

import typer
from rich.console                                                                   import Console

from sgraph_ai_service_playwright__cli.docker.cli.Renderers                         import (render_create,
                                                                                              render_health,
                                                                                              render_info  ,
                                                                                              render_list  )
from sgraph_ai_service_playwright__cli.docker.collections.List__Port                import List__Port
from sgraph_ai_service_playwright__cli.docker.schemas.Schema__Docker__Create__Request import (Schema__Docker__Create__Request,
                                                                                              DEFAULT_API_KEY_NAME            )
from sgraph_ai_service_playwright__cli.docker.service.Docker__Service               import DEFAULT_REGION, Docker__Service


DEBUG_TRACE = False


app = typer.Typer(no_args_is_help=True, help='Manage ephemeral Docker EC2 stacks (AL2023 + Docker CE, SSM access).')


@app.callback()
def _docker_root(debug: bool = typer.Option(False, '--debug',
                                             help='Show full Python traceback on errors.')):
    """Manage ephemeral Docker EC2 stacks. Pass --debug before a sub-command for full tracebacks."""
    global DEBUG_TRACE
    DEBUG_TRACE = debug


def _service() -> Docker__Service:
    return Docker__Service().setup()


def _err_handler(fn):                                                               # Mirrors elastic.py aws_error_handler
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except typer.Exit:
            raise
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            console = Console(highlight=False, stderr=True)
            console.print()
            console.print(f'  [red]✗[/]  [bold]{type(exc).__name__}[/]: {exc}')
            if not DEBUG_TRACE:
                console.print('     [dim]› Re-run with [bold]sp docker --debug ...[/] to see the full traceback.[/]')
            if DEBUG_TRACE:
                console.print()
                console.print('[dim]── traceback ────────────────────────────────────[/]')
                console.print(traceback.format_exc(), end='')
            console.print()
            raise typer.Exit(2)
    return wrapped


def _ports(raw: Optional[List[int]]) -> List__Port:
    result = List__Port()
    for p in (raw or []):
        result.append(p)
    return result


def resolve_stack_name(service: Docker__Service, provided: Optional[str], region: str) -> str:
    """Auto-select when one stack exists, prompt when many, error when none."""
    if provided:
        return provided
    listing      = service.list_stacks(region)
    names        = [str(s.stack_name) for s in listing.stacks if str(s.stack_name)]
    region_label = str(listing.region) or 'the current region'

    if len(names) == 0:
        Console(highlight=False, stderr=True).print(
            f'\n  [yellow]No docker stacks in {region_label}.[/]  Run: [bold]sp docker create[/]\n')
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
def create(name          : Optional[str]       = typer.Argument(None, help='Stack name; auto-generated if omitted.'),
           region        : str                 = typer.Option(DEFAULT_REGION,    '--region',       '-r', help='AWS region.'),
           instance_type : str                 = typer.Option('t3.medium',       '--instance-type', '-t', help='EC2 instance type.'),
           from_ami      : Optional[str]       = typer.Option(None,              '--ami',                help='AMI ID; latest AL2023 used if omitted.'),
           caller_ip     : Optional[str]       = typer.Option(None,              '--caller-ip',          help='Source IP; auto-detected if omitted.'),
           api_key_name  : str                 = typer.Option(DEFAULT_API_KEY_NAME, '--api-key-name',    help='Header name for host control plane auth.'),
           api_key_value : Optional[str]       = typer.Option(None,              '--api-key-value',      help='Host control plane API key; auto-generated if omitted.'),
           max_hours     : int                 = typer.Option(1,                 '--max-hours',          help='Auto-terminate after N hours; 0 = no timer.'),
           extra_ports   : Optional[List[int]] = typer.Option(None,              '--port',               help='Extra TCP ports to open (repeatable).'),
           wait          : bool                = typer.Option(False,             '--wait',               help='Block until Docker is installed and running (timeout 600s).'),
           open_browser  : bool                = typer.Option(False,             '--open',               help='Open host control plane docs in browser after ready.')):
    """Provision an AL2023 EC2 stack with Docker CE installed."""
    c       = Console(highlight=False, width=200)
    svc     = _service()
    request = Schema__Docker__Create__Request(
        stack_name    = name          or ''           ,
        region        = region                        ,
        instance_type = instance_type                 ,
        from_ami      = from_ami      or ''           ,
        caller_ip     = caller_ip     or ''           ,
        api_key_name  = api_key_name                  ,
        api_key_value = api_key_value or ''           ,
        max_hours     = max_hours                     ,
        extra_ports   = _ports(extra_ports)           )
    resp = svc.create_stack(request)
    render_create(resp, c)
    if wait:
        import webbrowser
        stack_name = str(resp.stack_info.stack_name)
        c.print(f'  [dim]Waiting for {stack_name!r} to become Docker-ready (timeout=600s)…[/]')
        h = svc.health(region, stack_name, timeout_sec=600, poll_sec=15)
        render_health(h, c)
        if not h.healthy:
            raise typer.Exit(1)
        if open_browser and str(h.public_ip):
            url = f'http://{str(h.public_ip)}:9000/docs'
            c.print(f'  [dim]Opening {url}[/]')
            webbrowser.open(url)


@app.command(name='list')
@_err_handler
def list_stacks(region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """List all Docker stacks in the region."""
    listing = _service().list_stacks(region)
    render_list(listing, Console(highlight=False, width=200))


@app.command()
@_err_handler
def info(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         region: str           = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Show details for a single Docker stack."""
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = resolve_stack_name(svc, name, region)
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No Docker stack matched {name!r}[/]')
        raise typer.Exit(1)
    render_info(data, c)


@app.command()
@_err_handler
def delete(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
           region: str           = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Terminate a Docker stack."""
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = resolve_stack_name(svc, name, region)
    resp = svc.delete_stack(region, name)
    if not resp.deleted:
        c.print(f'  [red]✗  {resp.message}[/]')
        raise typer.Exit(1)
    c.print(f'  ✅  {resp.message}  [dim]({resp.elapsed_ms / 1000:.1f}s)[/]')


@app.command()
@_err_handler
def wait(name         : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         region       : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
         timeout_sec  : int           = typer.Option(600            , '--timeout', help='Max seconds to wait for Docker readiness.'),
         poll_sec     : int           = typer.Option(15             , '--poll'   , help='Seconds between polls.'),
         open_browser : bool          = typer.Option(False          , '--open'   , help='Open host control plane docs in browser after ready.')):
    """Wait until Docker is installed and running on the stack."""
    import webbrowser
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = resolve_stack_name(svc, name, region)
    c.print(f'  [dim]Waiting for {name!r} to become Docker-ready (timeout={timeout_sec}s)…[/]')
    h = svc.health(region, name, timeout_sec=timeout_sec, poll_sec=poll_sec)
    render_health(h, c)
    if not h.healthy:
        raise typer.Exit(1)
    if open_browser and str(h.public_ip):
        url = f'http://{str(h.public_ip)}:9000/docs'
        c.print(f'  [dim]Opening {url}[/]')
        webbrowser.open(url)


@app.command()
@_err_handler
def health(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
           region: str           = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Quick Docker + SSM reachability probe (no waiting)."""
    svc  = _service()
    name = resolve_stack_name(svc, name, region)
    h    = svc.health(region, name, timeout_sec=0, poll_sec=1)
    render_health(h, Console(highlight=False, width=200))


@app.command()
@_err_handler
def connect(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
            region: str           = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Open an SSM shell session on the stack (replaces current process with aws ssm start-session)."""
    import os
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = resolve_stack_name(svc, name, region)
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No Docker stack matched {name!r}[/]')
        raise typer.Exit(1)
    iid = str(data.instance_id)
    c.print(f'  [dim]Connecting to {name} ({iid}) in {region}…[/]\n')
    os.execvp('aws', ['aws', 'ssm', 'start-session', '--target', iid, '--region', region])
