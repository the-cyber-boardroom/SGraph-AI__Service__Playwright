# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — opensearch.py
# CLI entry-point: sp opensearch (alias: sp os)
# Manage ephemeral OpenSearch + Dashboards EC2 stacks.
#
# This module is the thin Typer wrapper. All logic lives in OpenSearch__Service —
# the CLI only constructs the service, calls one method, and renders the
# result via the Renderers helper. Same Tier-2A pattern as scripts/elastic.py.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional

import typer
from rich.console                                                                   import Console

from sgraph_ai_service_playwright__cli.opensearch.cli.Renderers                     import (render_create,
                                                                                              render_health,
                                                                                              render_info  ,
                                                                                              render_list  )
from sgraph_ai_service_playwright__cli.opensearch.schemas.Schema__OS__Stack__Create__Request import Schema__OS__Stack__Create__Request
from sgraph_ai_service_playwright__cli.opensearch.service.OpenSearch__Service       import DEFAULT_REGION, OpenSearch__Service


app = typer.Typer(no_args_is_help=True, help='Manage ephemeral OpenSearch + Dashboards EC2 stacks.')


def _service() -> OpenSearch__Service:                                              # Single seam — tests override to inject an in-memory fake
    return OpenSearch__Service().setup()


@app.command()
def create(name           : Optional[str] = typer.Argument(None, help='Stack name; auto-generated as os-{adjective}-{scientist} if omitted.'),
           region         : str           = typer.Option(DEFAULT_REGION, '--region', '-r', help='AWS region.'),
           instance_type  : str           = typer.Option('t3.large'    , '--instance-type', '-t', help='EC2 instance type.'),
           admin_password : Optional[str] = typer.Option(None, '--password', '-p', help='Admin password; generated if omitted (returned once).'),
           no_spot        : bool          = typer.Option(False          , '--no-spot'      , help='Use on-demand instance instead of spot.')):
    """Provision an OpenSearch + Dashboards EC2 stack."""
    request = Schema__OS__Stack__Create__Request(stack_name     = name           or '',
                                                  region         = region              ,
                                                  instance_type  = instance_type       ,
                                                  admin_password = admin_password or '',
                                                  use_spot       = not no_spot         )
    resp = _service().create_stack(request)
    render_create(resp, Console(highlight=False, width=200))


@app.command(name='list')
def list_stacks(region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """List all OpenSearch stacks in the region."""
    listing = _service().list_stacks(region)
    render_list(listing, Console(highlight=False, width=200))


@app.command()
def info(name: str = typer.Argument(..., help='Stack name.'),
         region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Show details for a single OpenSearch stack."""
    c    = Console(highlight=False, width=200)
    info = _service().get_stack_info(region, name)
    if info is None:
        c.print(f'  [red]✗  No OpenSearch stack matched {name!r}[/]')
        raise typer.Exit(1)
    render_info(info, c)


@app.command()
def delete(name: str = typer.Argument(..., help='Stack name.'),
           region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Terminate an OpenSearch stack."""
    c    = Console(highlight=False, width=200)
    resp = _service().delete_stack(region, name)
    if not resp.terminated_instance_ids:
        c.print(f'  [red]✗  No OpenSearch stack matched {name!r}[/]')
        raise typer.Exit(1)
    ids = [str(iid) for iid in resp.terminated_instance_ids]
    c.print(f'  ✅  Terminated {len(ids)} instance(s): [dim]{", ".join(ids)}[/]')


@app.command()
def health(name: str = typer.Argument(..., help='Stack name.'),
           region: str = typer.Option(DEFAULT_REGION, '--region', '-r'),
           username: str = typer.Option('admin', '--user', '-u'),
           password: str = typer.Option('', '--password', '-p', help='Admin password (defaults to empty for unauthenticated probes).')):
    """Probe cluster + dashboards health on the live stack."""
    h = _service().health(region, name, username, password)
    render_health(h, Console(highlight=False, width=200))
