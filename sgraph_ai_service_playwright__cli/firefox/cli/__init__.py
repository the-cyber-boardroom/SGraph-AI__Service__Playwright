# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — sp firefox
# Typer CLI for managing ephemeral Firefox (jlesage/firefox noVNC) EC2 stacks
# with mitmproxy for traffic inspection.
# All logic lives in Firefox__Service — this file only constructs the service,
# calls one method, and renders via Renderers. Tier-2A pattern.
#
# Commands:
#   sp firefox create [name]      — provision a Firefox + mitmproxy stack
#   sp firefox list               — list all Firefox stacks in region
#   sp firefox info [name]        — show stack details (viewer + mitmweb URLs)
#   sp firefox wait [name]        — block until instance is running
#   sp firefox health [name]      — instant EC2 state probe
#   sp firefox delete [name]      — terminate a stack
#   sp firefox connect [name]     — open an SSM shell on the instance
#   sp firefox interceptors       — list baked mitmproxy interceptor examples
# ═══════════════════════════════════════════════════════════════════════════════

import functools
import traceback
from typing                                                                         import Optional

import typer
from rich.console                                                                   import Console

from sgraph_ai_service_playwright__cli.firefox.cli.Renderers                        import (render_create       ,
                                                                                             render_health       ,
                                                                                             render_info         ,
                                                                                             render_interceptors ,
                                                                                             render_list         )
from sgraph_ai_service_playwright__cli.firefox.enums.Enum__Firefox__Interceptor__Kind       import Enum__Firefox__Interceptor__Kind
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Interceptor__Choice import Schema__Firefox__Interceptor__Choice
from sgraph_ai_service_playwright__cli.firefox.schemas.Schema__Firefox__Stack__Create__Request import Schema__Firefox__Stack__Create__Request
from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Interceptor__Resolver import list_examples
from sgraph_ai_service_playwright__cli.firefox.service.Firefox__Service             import DEFAULT_INSTANCE_TYPE, DEFAULT_REGION, Firefox__Service


DEBUG_TRACE = False

app = typer.Typer(no_args_is_help=True,
                  help='Manage ephemeral Firefox (noVNC browser) EC2 stacks with mitmproxy traffic inspection.')


@app.callback()
def _firefox_root(debug: bool = typer.Option(False, '--debug',
                                              help='Show full Python traceback on errors.')):
    """Manage ephemeral Firefox noVNC browser stacks. Pass --debug for full tracebacks."""
    global DEBUG_TRACE
    DEBUG_TRACE = debug


def _service() -> Firefox__Service:
    return Firefox__Service().setup()


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
            console = Console(highlight=False, stderr=True)
            console.print()
            console.print(f'  [red]✗[/]  [bold]{type(exc).__name__}[/]: {exc}')
            if not DEBUG_TRACE:
                console.print('     [dim]› Re-run with [bold]sp firefox --debug ...[/] for the full traceback.[/]')
            else:
                console.print()
                console.print('[dim]── traceback ────────────────────────────────────[/]')
                console.print(traceback.format_exc(), end='')
            console.print()
            raise typer.Exit(2)
    return wrapped


def _interceptor_choice(name: Optional[str], script_path: Optional[str]) -> Schema__Firefox__Interceptor__Choice:
    if name and script_path:
        raise typer.BadParameter('Pass at most one of --interceptor / --interceptor-script.')
    if name:
        return Schema__Firefox__Interceptor__Choice(kind=Enum__Firefox__Interceptor__Kind.NAME, name=name)
    if script_path:
        with open(script_path, 'r', encoding='utf-8') as fh:
            source = fh.read()
        return Schema__Firefox__Interceptor__Choice(kind=Enum__Firefox__Interceptor__Kind.INLINE, inline_source=source)
    return Schema__Firefox__Interceptor__Choice()                                   # NONE


def _resolve_stack_name(service: Firefox__Service, provided: Optional[str], region: str) -> str:
    """Auto-select when one stack exists, prompt when many, error when none."""
    if provided:
        return provided
    listing      = service.list_stacks(region)
    names        = [str(s.stack_name) for s in listing.stacks if str(s.stack_name)]
    region_label = str(listing.region) or region

    if len(names) == 0:
        Console(highlight=False, stderr=True).print(
            f'\n  [yellow]No Firefox stacks in {region_label}.[/]  Run: [bold]sp firefox create[/]\n')
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


# ── commands ──────────────────────────────────────────────────────────────────

@app.command()
@_err_handler
def create(name              : Optional[str] = typer.Argument(None, help='Stack name; auto-generated as firefox-{adjective}-{scientist} if omitted.'),
           region            : str           = typer.Option(DEFAULT_REGION       , '--region'           , '-r', help='AWS region.'),
           instance_type     : str           = typer.Option(DEFAULT_INSTANCE_TYPE, '--instance-type'    , '-t', help='EC2 instance type.'),
           from_ami          : Optional[str] = typer.Option(None                 , '--ami'              ,       help='AMI ID; latest AL2023 used if omitted.'),
           caller_ip         : Optional[str] = typer.Option(None                 , '--caller-ip'        ,       help='Source IP for SG rule; auto-detected if omitted.'),
           password          : Optional[str] = typer.Option(None                 , '--password'         ,       help='Web UI password. Auto-generated if omitted.'),
           interceptor       : Optional[str] = typer.Option(None                 , '--interceptor'      ,       help='Name of a baked mitmproxy interceptor (see `sp firefox interceptors`).'),
           interceptor_script: Optional[str] = typer.Option(None                 , '--interceptor-script',      help='Path to a local Python file; embedded inline at create time.'),
           wait              : bool          = typer.Option(False                , '--wait'             ,       help='Block until instance is running.')):
    """Provision a Firefox (noVNC browser) + mitmproxy EC2 stack."""
    c       = Console(highlight=False, width=200)
    choice  = _interceptor_choice(interceptor, interceptor_script)
    request = Schema__Firefox__Stack__Create__Request(
        stack_name    = name          or '',
        region        = region             ,
        instance_type = instance_type      ,
        from_ami      = from_ami      or '',
        caller_ip     = caller_ip     or '',
        password      = password      or '',
        interceptor   = choice             )
    svc  = _service()
    resp = svc.create_stack(request)
    render_create(resp, c)
    if wait:
        stack_name = str(resp.stack_name)
        c.print(f'  [dim]Waiting for {stack_name!r} to become running…[/]')
        h = svc.health(region, stack_name, timeout_sec=300, poll_sec=10)
        render_health(h, c)
        if not h.healthy:
            raise typer.Exit(1)
        data = svc.get_stack_info(region, stack_name)
        if data:
            render_info(data, c)


@app.command(name='list')
@_err_handler
def list_stacks(region: str = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    """List all Firefox stacks in the region."""
    render_list(_service().list_stacks(region), Console(highlight=False, width=200))


@app.command()
@_err_handler
def info(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         region: str           = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    """Show details for a single Firefox stack (includes viewer and mitmweb URLs once running)."""
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = _resolve_stack_name(svc, name, region)
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No Firefox stack matched {name!r}[/]')
        raise typer.Exit(1)
    render_info(data, c)


@app.command()
@_err_handler
def wait(name       : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         region     : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
         timeout_sec: int           = typer.Option(300            , '--timeout', help='Max seconds to wait.'),
         poll_sec   : int           = typer.Option(10             , '--poll'   , help='Seconds between polls.')):
    """Wait until the Firefox instance is running."""
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = _resolve_stack_name(svc, name, region)
    c.print(f'  [dim]Waiting for {name!r} to become running (timeout={timeout_sec}s)…[/]')
    h = svc.health(region, name, timeout_sec=timeout_sec, poll_sec=poll_sec)
    render_health(h, c)
    if not h.healthy:
        raise typer.Exit(1)


@app.command()
@_err_handler
def health(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
           region: str           = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Quick EC2 state probe (no waiting)."""
    svc  = _service()
    name = _resolve_stack_name(svc, name, region)
    h    = svc.health(region, name, timeout_sec=0, poll_sec=1)
    render_health(h, Console(highlight=False, width=200))


@app.command()
@_err_handler
def delete(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
           region: str           = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    """Terminate a Firefox stack."""
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = _resolve_stack_name(svc, name, region)
    resp = svc.delete_stack(region, name)
    if not resp.deleted:
        c.print(f'  [red]✗  {resp.message}[/]')
        raise typer.Exit(1)
    c.print(f'  ✅  {resp.message}  [dim]({resp.elapsed_ms / 1000:.1f}s)[/]')


@app.command()
@_err_handler
def connect(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
            region: str           = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.')):
    """Open an SSM shell session on the Firefox stack instance."""
    import os
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = _resolve_stack_name(svc, name, region)
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No Firefox stack matched {name!r}[/]')
        raise typer.Exit(1)
    iid = str(data.instance_id)
    c.print(f'  [dim]Connecting to {name} ({iid}) in {region}…[/]\n')
    os.execvp('aws', ['aws', 'ssm', 'start-session', '--target', iid, '--region', region])


@app.command()
@_err_handler
def interceptors():
    """List baked mitmproxy interceptor examples (pass name to --interceptor on create)."""
    render_interceptors(list_examples(), Console(highlight=False, width=200))
