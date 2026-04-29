# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — vnc.py
# CLI entry-point: sp vnc
# Manage ephemeral chromium + nginx + mitmproxy EC2 stacks (browser-viewer).
#
# Thin Typer wrapper. All logic lives in Vnc__Service — the CLI only
# constructs the service, calls one method, and renders via the Renderers
# helper. Same Tier-2A pattern as scripts/linux.py / scripts/docker_stack.py /
# scripts/prometheus.py / scripts/opensearch.py.
# ═══════════════════════════════════════════════════════════════════════════════

import functools
import time
import traceback
from typing                                                                         import Optional

import typer
from rich.console                                                                   import Console

from sgraph_ai_service_playwright__cli.vnc.cli.Renderers                            import (render_create      ,
                                                                                              render_flows       ,
                                                                                              render_health      ,
                                                                                              render_info        ,
                                                                                              render_interceptors,
                                                                                              render_list        )
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Interceptor__Kind       import Enum__Vnc__Interceptor__Kind
from sgraph_ai_service_playwright__cli.vnc.enums.Enum__Vnc__Stack__State            import Enum__Vnc__Stack__State
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Health              import Schema__Vnc__Health
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Interceptor__Choice import Schema__Vnc__Interceptor__Choice
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Request import Schema__Vnc__Stack__Create__Request
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Interceptor__Resolver       import list_examples
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Service                     import DEFAULT_INSTANCE_TYPE, DEFAULT_REGION, Vnc__Service


DEBUG_TRACE = False


app = typer.Typer(no_args_is_help=True, help='Manage ephemeral chromium + nginx + mitmproxy EC2 stacks (browser-viewer).')


@app.callback()
def _vnc_root(debug: bool = typer.Option(False, '--debug',
                                           help='Show full Python traceback on errors.')):
    """Manage ephemeral browser-viewer stacks. Pass --debug before a sub-command for full tracebacks."""
    global DEBUG_TRACE
    DEBUG_TRACE = debug


def _service() -> Vnc__Service:                                                     # Single seam — tests override to inject an in-memory fake
    return Vnc__Service().setup()


def _err_handler(fn):                                                               # Mirrors linux.py / docker_stack.py — friendly errors, full trace with --debug
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
                console.print('     [dim]› Re-run with [bold]sp vnc --debug ...[/] to see the full traceback.[/]')
            if DEBUG_TRACE:
                console.print()
                console.print('[dim]── traceback ────────────────────────────────────[/]')
                console.print(traceback.format_exc(), end='')
            console.print()
            raise typer.Exit(2)
    return wrapped


def _interceptor_choice(name: Optional[str], script_path: Optional[str]) -> Schema__Vnc__Interceptor__Choice:    # N5 selector
    if name and script_path:
        raise typer.BadParameter('Pass at most one of --interceptor / --interceptor-script.')
    if name:
        return Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.NAME, name=name)
    if script_path:
        with open(script_path, 'r', encoding='utf-8') as fh:
            source = fh.read()
        return Schema__Vnc__Interceptor__Choice(kind=Enum__Vnc__Interceptor__Kind.INLINE, inline_source=source)
    return Schema__Vnc__Interceptor__Choice()                                       # NONE — N5 default-off


def resolve_stack_name(service: Vnc__Service, provided: Optional[str], region: str) -> str:
    """Auto-select when one stack exists, prompt when many, error when none."""
    if provided:
        return provided
    listing      = service.list_stacks(region)
    names        = [str(s.stack_name) for s in listing.stacks if str(s.stack_name)]
    region_label = str(listing.region) or 'the current region'

    if len(names) == 0:
        Console(highlight=False, stderr=True).print(
            f'\n  [yellow]No VNC stacks in {region_label}.[/]  Run: [bold]sp vnc create[/]\n')
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


def _wait_for_ready(service: Vnc__Service, region: str, name: str, username: str, password: str,
                     timeout_sec: int, poll_sec: int, c: Console) -> Schema__Vnc__Health:
    """Poll Vnc__Service.health until both nginx_ok and mitmweb_ok, or timeout."""
    deadline = time.monotonic() + max(timeout_sec, 0)
    last     = service.health(region, name, username, password)
    while not (last.nginx_ok and last.mitmweb_ok) and time.monotonic() < deadline:
        c.print(f'  [dim]…still booting (state={last.state.value}, '
                  f'nginx={"ok" if last.nginx_ok else "no"}, '
                  f'mitmweb={"ok" if last.mitmweb_ok else "no"}); sleeping {poll_sec}s[/]')
        time.sleep(max(poll_sec, 1))
        last = service.health(region, name, username, password)
    return last


@app.command()
@_err_handler
def create(name             : Optional[str] = typer.Argument(None, help='Stack name; auto-generated as vnc-{adjective}-{scientist} if omitted.'),
           region           : str           = typer.Option(DEFAULT_REGION       , '--region', '-r', help='AWS region.'),
           instance_type    : str           = typer.Option(DEFAULT_INSTANCE_TYPE, '--instance-type', '-t', help='EC2 instance type.'),
           password         : Optional[str] = typer.Option(None, '--password'           , '-p',
                                                             help='Operator password for nginx Basic auth + mitmproxy proxy auth. '
                                                                  'URL-safe base64, 16-64 chars. Auto-generated if omitted (returned once on create).'),
           interceptor      : Optional[str] = typer.Option(None, '--interceptor'         , help='Name of a baked example interceptor (see `sp vnc interceptors`).'),
           interceptor_script: Optional[str] = typer.Option(None, '--interceptor-script' , help='Path to a local Python file; embedded inline at create time.'),
           wait             : bool           = typer.Option(False, '--wait'              , help='Block until nginx + mitmweb are reachable (timeout 600s).')):
    """Provision a chromium + nginx + mitmproxy EC2 stack."""
    c       = Console(highlight=False, width=200)
    svc     = _service()
    choice  = _interceptor_choice(interceptor, interceptor_script)
    request = Schema__Vnc__Stack__Create__Request(stack_name        = name           or '',
                                                    region            = region              ,
                                                    instance_type     = instance_type       ,
                                                    operator_password = password       or '',
                                                    interceptor       = choice              )
    resp = svc.create_stack(request)
    render_create(resp, c)
    if wait:
        stack_name = str(resp.stack_name)
        password   = str(resp.operator_password)
        c.print(f'  [dim]Waiting for {stack_name!r} to become reachable (nginx + mitmweb)…[/]')
        h = _wait_for_ready(svc, region, stack_name, 'operator', password,
                              timeout_sec=600, poll_sec=15, c=c)
        render_health(h, c)
        if not (h.nginx_ok and h.mitmweb_ok):
            raise typer.Exit(1)


@app.command(name='list')
@_err_handler
def list_stacks(region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """List all VNC stacks in the region."""
    listing = _service().list_stacks(region)
    render_list(listing, Console(highlight=False, width=200))


@app.command()
@_err_handler
def info(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         region: str           = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Show details for a single VNC stack."""
    c       = Console(highlight=False, width=200)
    svc     = _service()
    name    = resolve_stack_name(svc, name, region)
    c.print(f'  [dim]Fetching {name!r} from {region}…[/]')                          # Progress hint — boto3 describe_instances is silent and can take 1-3s
    data    = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No VNC stack matched {name!r}[/]')
        raise typer.Exit(1)
    render_info(data, c)


@app.command()
@_err_handler
def delete(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
           region: str           = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Terminate a VNC stack. All state on the EC2 is wiped (per N3)."""
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = resolve_stack_name(svc, name, region)
    resp = svc.delete_stack(region, name)
    if not resp.terminated_instance_ids:
        c.print(f'  [red]✗  No VNC stack matched {name!r}[/]')
        raise typer.Exit(1)
    ids = [str(iid) for iid in resp.terminated_instance_ids]
    c.print(f'  ✅  Terminated {len(ids)} instance(s): [dim]{", ".join(ids)}[/]')


@app.command()
@_err_handler
def health(name    : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
           region  : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
           username: str           = typer.Option('operator', '--user'    , '-u'),
           password: str           = typer.Option('',         '--password', '-p', help='Operator password (returned once on create).')):
    """Probe nginx + mitmweb reachability on the live stack (no waiting)."""
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = resolve_stack_name(svc, name, region)
    c.print(f'  [dim]Probing {name!r}…[/]')                                          # Progress hint — boto3 + 2 HTTP probes can take 5-10s
    h    = svc.health(region, name, username, password)
    render_health(h, c)


@app.command()
@_err_handler
def wait(name       : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
         region     : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
         username   : str           = typer.Option('operator', '--user'    , '-u'),
         password   : str           = typer.Option('',         '--password', '-p'),
         timeout_sec: int           = typer.Option(600, '--timeout', help='Max seconds to wait for nginx + mitmweb readiness.'),
         poll_sec   : int           = typer.Option(15 , '--poll'   , help='Seconds between polls.')):
    """Wait until the stack's nginx + mitmweb are reachable."""
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = resolve_stack_name(svc, name, region)
    c.print(f'  [dim]Waiting for {name!r} (timeout={timeout_sec}s, poll={poll_sec}s)…[/]')
    h = _wait_for_ready(svc, region, name, username, password,
                          timeout_sec=timeout_sec, poll_sec=poll_sec, c=c)
    render_health(h, c)
    if not (h.nginx_ok and h.mitmweb_ok):
        raise typer.Exit(1)


@app.command()
@_err_handler
def flows(name    : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
          region  : str           = typer.Option(DEFAULT_REGION, '--region', '-r'),
          username: str           = typer.Option('operator', '--user'    , '-u'),
          password: str           = typer.Option('',         '--password', '-p')):
    """List recent mitmweb flows on the live stack (no auto-export per N4)."""
    c       = Console(highlight=False, width=200)
    svc     = _service()
    name    = resolve_stack_name(svc, name, region)
    c.print(f'  [dim]Fetching mitmweb flows from {name!r}…[/]')
    listing = svc.flows(region, name, username, password)
    render_flows(listing, c)


@app.command()
@_err_handler
def connect(name  : Optional[str] = typer.Argument(None, help='Stack name; auto-selected when only one exists.'),
            region: str           = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Open an SSM shell session on the stack (replaces current process with aws ssm start-session)."""
    import os
    c    = Console(highlight=False, width=200)
    svc  = _service()
    name = resolve_stack_name(svc, name, region)
    c.print(f'  [dim]Resolving {name!r}…[/]')
    data = svc.get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No VNC stack matched {name!r}[/]')
        raise typer.Exit(1)
    iid = str(data.instance_id)
    c.print(f'  [dim]Connecting to {name} ({iid}) in {region}…[/]\n')
    os.execvp('aws', ['aws', 'ssm', 'start-session', '--target', iid, '--region', region])


@app.command()
@_err_handler
def interceptors():
    """List the baked example interceptors that ship with sp vnc."""
    render_interceptors(list_examples(), Console(highlight=False, width=200))
