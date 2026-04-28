# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — linux.py
# CLI entry-point: sp linux
# Manage ephemeral bare Linux EC2 stacks (AL2023 + SSM access, no SSH).
#
# Tier-2A thin Typer wrapper — all logic lives in Linux__Service; this module
# only constructs the service, calls one method, and renders via Renderers.
# ═══════════════════════════════════════════════════════════════════════════════

import functools
import traceback
from typing                                                                         import List, Optional

import typer
from rich.console                                                                   import Console

from sgraph_ai_service_playwright__cli.linux.cli.Renderers                          import (render_create,
                                                                                              render_health,
                                                                                              render_info  ,
                                                                                              render_list  )
from sgraph_ai_service_playwright__cli.linux.collections.List__Port                 import List__Port
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Create__Request import Schema__Linux__Create__Request
from sgraph_ai_service_playwright__cli.linux.service.Linux__Service                 import DEFAULT_REGION, Linux__Service


DEBUG_TRACE = False


app = typer.Typer(no_args_is_help=True, help='Manage ephemeral Linux EC2 stacks (AL2023, SSM access).')


@app.callback()
def _linux_root(debug: bool = typer.Option(False, '--debug',
                                            help='Show full Python traceback on errors.')):
    """Manage ephemeral Linux EC2 stacks. Pass --debug before a sub-command for full tracebacks."""
    global DEBUG_TRACE
    DEBUG_TRACE = debug


def _service() -> Linux__Service:                                                   # Single seam — tests override to inject an in-memory fake
    return Linux__Service().setup()


def _err_handler(fn):                                                               # Mirrors elastic.py aws_error_handler — friendly errors, full trace with --debug
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
                console.print('     [dim]› Re-run with [bold]sp linux --debug ...[/] to see the full traceback.[/]')
            if DEBUG_TRACE:
                console.print()
                console.print('[dim]── traceback ────────────────────────────────────[/]')
                console.print(traceback.format_exc(), end='')
            console.print()
            raise typer.Exit(2)
    return wrapped


def _ports(raw: Optional[List[int]]) -> List__Port:                                 # Typer passes plain list[int]; wrap in Type_Safe collection
    result = List__Port()
    for p in (raw or []):
        result.append(p)
    return result


@app.command()
@_err_handler
def create(name          : Optional[str]       = typer.Argument(None, help='Stack name; auto-generated as {adjective}-{scientist} if omitted.'),
           region        : str                 = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.'),
           instance_type : str                 = typer.Option('t3.medium'   , '--instance-type', '-t', help='EC2 instance type.'),
           from_ami      : Optional[str]       = typer.Option(None          , '--ami'           , help='AMI ID; latest AL2023 used if omitted.'),
           caller_ip     : Optional[str]       = typer.Option(None          , '--caller-ip'     , help='Source IP for SG rule; auto-detected if omitted.'),
           max_hours     : int                 = typer.Option(1             , '--max-hours'     , help='Auto-terminate after N hours; 0 = no timer.'),
           extra_ports   : Optional[List[int]] = typer.Option(None          , '--port'          , help='Extra TCP ports to open from caller /32 (repeatable).'),
           wait          : bool                = typer.Option(False         , '--wait'          , help='Block until instance is running and SSM-reachable.')):
    """Provision a bare Linux EC2 stack with SSM access."""
    c       = Console(highlight=False, width=200)
    svc     = _service()
    request = Schema__Linux__Create__Request(
        stack_name    = name          or ''      ,
        region        = region                   ,
        instance_type = instance_type            ,
        from_ami      = from_ami      or ''      ,
        caller_ip     = caller_ip     or ''      ,
        max_hours     = max_hours                ,
        extra_ports   = _ports(extra_ports)      )
    resp = svc.create_stack(request)
    render_create(resp, c)
    if wait:
        stack_name = str(resp.stack_info.stack_name)
        c.print(f'  [dim]Waiting for {stack_name!r} to become SSM-reachable…[/]')
        h = svc.health(region, stack_name, timeout_sec=300, poll_sec=10)
        render_health(h, c)
        if not h.healthy:
            raise typer.Exit(1)


@app.command(name='list')
@_err_handler
def list_stacks(region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """List all Linux stacks in the region."""
    listing = _service().list_stacks(region)
    render_list(listing, Console(highlight=False, width=200))


@app.command()
@_err_handler
def info(name  : str = typer.Argument(..., help='Stack name.'),
         region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Show details for a single Linux stack."""
    c    = Console(highlight=False, width=200)
    data = _service().get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No Linux stack matched {name!r}[/]')
        raise typer.Exit(1)
    render_info(data, c)


@app.command()
@_err_handler
def delete(name  : str = typer.Argument(..., help='Stack name.'),
           region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Terminate a Linux stack."""
    c    = Console(highlight=False, width=200)
    resp = _service().delete_stack(region, name)
    if not resp.deleted:
        c.print(f'  [red]✗  {resp.message}[/]')
        raise typer.Exit(1)
    c.print(f'  ✅  {resp.message}  [dim]({resp.elapsed_ms}ms)[/]')


@app.command()
@_err_handler
def wait(name       : str = typer.Argument(..., help='Stack name.'),
         region     : str = typer.Option(DEFAULT_REGION, '--region', '-r'),
         timeout_sec: int = typer.Option(300            , '--timeout', help='Max seconds to wait for SSM readiness.'),
         poll_sec   : int = typer.Option(10             , '--poll'   , help='Seconds between polls.')):
    """Wait until the stack is running and SSM-reachable."""
    c = Console(highlight=False, width=200)
    c.print(f'  [dim]Waiting for {name!r} to become SSM-reachable (timeout={timeout_sec}s)…[/]')
    h = _service().health(region, name, timeout_sec=timeout_sec, poll_sec=poll_sec)
    render_health(h, c)
    if not h.healthy:
        raise typer.Exit(1)


@app.command()
@_err_handler
def health(name  : str = typer.Argument(..., help='Stack name.'),
           region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Quick SSM reachability probe (no waiting)."""
    h = _service().health(region, name, timeout_sec=0, poll_sec=1)
    render_health(h, Console(highlight=False, width=200))


@app.command()
@_err_handler
def connect(name  : str = typer.Argument(..., help='Stack name.'),
            region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Print the aws ssm start-session command for this stack."""
    c    = Console(highlight=False, width=200)
    data = _service().get_stack_info(region, name)
    if data is None:
        c.print(f'  [red]✗  No Linux stack matched {name!r}[/]')
        raise typer.Exit(1)
    iid = str(data.instance_id)
    c.print(f'\n  [bold]aws ssm start-session --target {iid} --region {region}[/]\n')
