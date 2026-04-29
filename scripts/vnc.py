# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — vnc.py
# CLI entry-point: sp vnc
# Manage ephemeral chromium + nginx + mitmproxy EC2 stacks (browser-viewer).
#
# Thin Typer wrapper. All logic lives in Vnc__Service — the CLI only
# constructs the service, calls one method, and renders via the Renderers
# helper. Same Tier-2A pattern as scripts/prometheus.py / scripts/opensearch.py.
# ═══════════════════════════════════════════════════════════════════════════════

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
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Interceptor__Choice import Schema__Vnc__Interceptor__Choice
from sgraph_ai_service_playwright__cli.vnc.schemas.Schema__Vnc__Stack__Create__Request import Schema__Vnc__Stack__Create__Request
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Interceptor__Resolver       import list_examples
from sgraph_ai_service_playwright__cli.vnc.service.Vnc__Service                     import DEFAULT_INSTANCE_TYPE, DEFAULT_REGION, Vnc__Service


app = typer.Typer(no_args_is_help=True, help='Manage ephemeral chromium + nginx + mitmproxy EC2 stacks (browser-viewer).')


def _service() -> Vnc__Service:                                                     # Single seam — tests override to inject an in-memory fake
    return Vnc__Service().setup()


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


@app.command()
def create(name             : Optional[str] = typer.Argument(None, help='Stack name; auto-generated as vnc-{adjective}-{scientist} if omitted.'),
           region           : str           = typer.Option(DEFAULT_REGION       , '--region', '-r', help='AWS region.'),
           instance_type    : str           = typer.Option(DEFAULT_INSTANCE_TYPE, '--instance-type', '-t', help='EC2 instance type.'),
           interceptor      : Optional[str] = typer.Option(None, '--interceptor'         , help='Name of a baked example interceptor (see `sp vnc interceptors`).'),
           interceptor_script: Optional[str] = typer.Option(None, '--interceptor-script' , help='Path to a local Python file; embedded inline at create time.')):
    """Provision a chromium + nginx + mitmproxy EC2 stack."""
    choice  = _interceptor_choice(interceptor, interceptor_script)
    request = Schema__Vnc__Stack__Create__Request(stack_name    = name           or '',
                                                    region        = region              ,
                                                    instance_type = instance_type       ,
                                                    interceptor   = choice              )
    resp = _service().create_stack(request)
    render_create(resp, Console(highlight=False, width=200))


@app.command(name='list')
def list_stacks(region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """List all VNC stacks in the region."""
    listing = _service().list_stacks(region)
    render_list(listing, Console(highlight=False, width=200))


@app.command()
def info(name  : str = typer.Argument(..., help='Stack name.'),
         region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Show details for a single VNC stack."""
    c    = Console(highlight=False, width=200)
    info = _service().get_stack_info(region, name)
    if info is None:
        c.print(f'  [red]✗  No VNC stack matched {name!r}[/]')
        raise typer.Exit(1)
    render_info(info, c)


@app.command()
def delete(name  : str = typer.Argument(..., help='Stack name.'),
           region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Terminate a VNC stack. All state on the EC2 is wiped (per N3)."""
    c    = Console(highlight=False, width=200)
    resp = _service().delete_stack(region, name)
    if not resp.terminated_instance_ids:
        c.print(f'  [red]✗  No VNC stack matched {name!r}[/]')
        raise typer.Exit(1)
    ids = [str(iid) for iid in resp.terminated_instance_ids]
    c.print(f'  ✅  Terminated {len(ids)} instance(s): [dim]{", ".join(ids)}[/]')


@app.command()
def health(name    : str = typer.Argument(..., help='Stack name.'),
           region  : str = typer.Option(DEFAULT_REGION, '--region', '-r'),
           username: str = typer.Option('operator', '--user'    , '-u'),
           password: str = typer.Option('',         '--password', '-p', help='Operator password (returned once on create).')):
    """Probe nginx + mitmweb reachability on the live stack."""
    h = _service().health(region, name, username, password)
    render_health(h, Console(highlight=False, width=200))


@app.command()
def flows(name    : str = typer.Argument(..., help='Stack name.'),
          region  : str = typer.Option(DEFAULT_REGION, '--region', '-r'),
          username: str = typer.Option('operator', '--user'    , '-u'),
          password: str = typer.Option('',         '--password', '-p')):
    """List recent mitmweb flows on the live stack (no auto-export per N4)."""
    listing = _service().flows(region, name, username, password)
    render_flows(listing, Console(highlight=False, width=200))


@app.command()
def interceptors():
    """List the baked example interceptors that ship with sp vnc."""
    render_interceptors(list_examples(), Console(highlight=False, width=200))
