# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — prometheus.py
# CLI entry-point: sp prometheus (alias: sp prom)
# Manage ephemeral Prometheus + cAdvisor + node-exporter EC2 stacks.
#
# Thin Typer wrapper. All logic lives in Prometheus__Service — the CLI only
# constructs the service, calls one method, and renders the result via the
# Renderers helper. Same Tier-2A pattern as scripts/opensearch.py.
# ═══════════════════════════════════════════════════════════════════════════════

from typing                                                                         import Optional

import typer
from rich.console                                                                   import Console

from sgraph_ai_service_playwright__cli.prometheus.cli.Renderers                     import (render_create,
                                                                                              render_health,
                                                                                              render_info  ,
                                                                                              render_list  )
from sgraph_ai_service_playwright__cli.prometheus.schemas.Schema__Prom__Stack__Create__Request import Schema__Prom__Stack__Create__Request
from sgraph_ai_service_playwright__cli.prometheus.service.Prometheus__Service       import DEFAULT_INSTANCE_TYPE, DEFAULT_REGION, Prometheus__Service


app = typer.Typer(no_args_is_help=True, help='Manage ephemeral Prometheus + cAdvisor + node-exporter EC2 stacks.')


def _service() -> Prometheus__Service:                                              # Single seam — tests override to inject an in-memory fake
    return Prometheus__Service().setup()


@app.command()
def create(name           : Optional[str] = typer.Argument(None, help='Stack name; auto-generated as prom-{adjective}-{scientist} if omitted.'),
           region         : str           = typer.Option(DEFAULT_REGION       , '--region', '-r', help='AWS region.'),
           instance_type  : str           = typer.Option(DEFAULT_INSTANCE_TYPE, '--instance-type', '-t', help='EC2 instance type.')):
    """Provision a Prometheus + cAdvisor + node-exporter EC2 stack."""
    request = Schema__Prom__Stack__Create__Request(stack_name    = name           or '',
                                                    region        = region              ,
                                                    instance_type = instance_type       )
    resp = _service().create_stack(request)
    render_create(resp, Console(highlight=False, width=200))


@app.command(name='list')
def list_stacks(region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """List all Prometheus stacks in the region."""
    listing = _service().list_stacks(region)
    render_list(listing, Console(highlight=False, width=200))


@app.command()
def info(name  : str = typer.Argument(..., help='Stack name.'),
         region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Show details for a single Prometheus stack."""
    c    = Console(highlight=False, width=200)
    info = _service().get_stack_info(region, name)
    if info is None:
        c.print(f'  [red]✗  No Prometheus stack matched {name!r}[/]')
        raise typer.Exit(1)
    render_info(info, c)


@app.command()
def delete(name  : str = typer.Argument(..., help='Stack name.'),
           region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    """Terminate a Prometheus stack."""
    c    = Console(highlight=False, width=200)
    resp = _service().delete_stack(region, name)
    if not resp.terminated_instance_ids:
        c.print(f'  [red]✗  No Prometheus stack matched {name!r}[/]')
        raise typer.Exit(1)
    ids = [str(iid) for iid in resp.terminated_instance_ids]
    c.print(f'  ✅  Terminated {len(ids)} instance(s): [dim]{", ".join(ids)}[/]')


@app.command()
def health(name    : str = typer.Argument(..., help='Stack name.'),
           region  : str = typer.Option(DEFAULT_REGION, '--region', '-r'),
           username: str = typer.Option(''            , '--user'  , '-u', help='Optional Basic-auth username (only useful when wrapped in nginx).'),
           password: str = typer.Option(''            , '--password', '-p', help='Optional Basic-auth password.')):
    """Probe Prometheus + scrape-target health on the live stack."""
    h = _service().health(region, name, username, password)
    render_health(h, Console(highlight=False, width=200))
