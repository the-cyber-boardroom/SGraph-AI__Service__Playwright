# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — linux.py
# CLI entry-point: sp linux
# Manage ephemeral bare Linux EC2 stacks (AL2023 + SSM access, no SSH).
#
# Tier-2A thin Typer wrapper — all logic lives in Linux__Service; this module
# only constructs the service, calls one method, and renders via Renderers.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import List, Optional

import typer
from rich.console                                                                   import Console

from sgraph_ai_service_playwright__cli.linux.cli.Renderers                          import (render_create,
                                                                                              render_health,
                                                                                              render_info  ,
                                                                                              render_list  )
from sgraph_ai_service_playwright__cli.linux.schemas.Schema__Linux__Create__Request import Schema__Linux__Create__Request
from sgraph_ai_service_playwright__cli.linux.service.Linux__Service                 import DEFAULT_REGION, Linux__Service


app = typer.Typer(no_args_is_help=True, help='Manage ephemeral Linux EC2 stacks (AL2023, SSM access).')


def _service() -> Linux__Service:                                                   # Single seam — tests override to inject an in-memory fake
    return Linux__Service().setup()


@app.command()
def create(name          : Optional[str]       = typer.Argument(None, help='Stack name; auto-generated as {adjective}-{scientist} if omitted.'),
           region        : str                 = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.'),
           instance_type : str                 = typer.Option('t3.medium'   , '--instance-type', '-t', help='EC2 instance type.'),
           from_ami      : Optional[str]       = typer.Option(None          , '--ami'           , help='AMI ID; latest AL2023 used if omitted.'),
           caller_ip     : Optional[str]       = typer.Option(None          , '--caller-ip'     , help='Source IP for SG rule; auto-detected if omitted.'),
           max_hours     : int                 = typer.Option(4             , '--max-hours'     , help='Auto-terminate after N hours; 0 = no timer.'),
           extra_ports   : Optional[List[int]] = typer.Option(None          , '--port'          , help='Extra TCP ports to open from caller /32 (repeatable).')):
    """Provision a bare Linux EC2 stack with SSM access."""
    request = Schema__Linux__Create__Request(
        stack_name    = name          or ''   ,
        region        = region                ,
        instance_type = instance_type         ,
        from_ami      = from_ami      or ''   ,
        caller_ip     = caller_ip     or ''   ,
        max_hours     = max_hours             ,
        extra_ports   = list(extra_ports or []))
    resp = _service().create_stack(request)
    render_create(resp, Console(highlight=False, width=200))


@app.command(name='list')
def list_stacks(region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """List all Linux stacks in the region."""
    listing = _service().list_stacks(region)
    render_list(listing, Console(highlight=False, width=200))


@app.command()
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
def health(name  : str = typer.Argument(..., help='Stack name.'),
           region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Quick SSM reachability probe (no waiting)."""
    h = _service().health(region, name, timeout_sec=0, poll_sec=1)
    render_health(h, Console(highlight=False, width=200))


@app.command()
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
