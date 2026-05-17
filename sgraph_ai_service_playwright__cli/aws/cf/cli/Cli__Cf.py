# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Cf
# Typer CLI surface for CloudFront distribution management.
#
# Command tree:
#   sg aws cf distributions list             — list all CF distributions
#   sg aws cf distribution show <id>         — details of one distribution
#   sg aws cf distribution create ...        — create a new distribution
#   sg aws cf distribution disable <id>      — disable (required before delete)
#   sg aws cf distribution delete <id>       — delete a disabled distribution
#   sg aws cf distribution wait <id>         — wait until Deployed
#
# Mutations require SG_AWS__CF__ALLOW_MUTATIONS=1.
# ═══════════════════════════════════════════════════════════════════════════════

import json
import os
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Errors                                           import spec_cli_errors

from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__CF__Domain_Name   import Safe_Str__CF__Domain_Name
from sgraph_ai_service_playwright__cli.aws.cf.primitives.Safe_Str__Cert__Arn         import Safe_Str__Cert__Arn
from sgraph_ai_service_playwright__cli.aws.cf.schemas.Schema__CF__Create__Request    import Schema__CF__Create__Request
from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__AWS__Client        import CloudFront__AWS__Client

console = Console()

cf_app            = typer.Typer(name='cf',            help='CloudFront distribution management.',      no_args_is_help=True)
distributions_app = typer.Typer(name='distributions', help='Account-wide distribution listing.',       no_args_is_help=True)
distribution_app  = typer.Typer(name='distribution',  help='Operations on one CF distribution.',       no_args_is_help=True)

cf_app.add_typer(distributions_app, name='distributions')
cf_app.add_typer(distribution_app,  name='distribution')


def _mutation_guard():
    if not os.environ.get('SG_AWS__CF__ALLOW_MUTATIONS'):
        console.print('[red]Set SG_AWS__CF__ALLOW_MUTATIONS=1 to allow CloudFront mutations.[/red]')
        raise typer.Exit(1)


# ── distributions list ────────────────────────────────────────────────────────

@distributions_app.command('list')
@spec_cli_errors
def distributions_list(
    as_json: bool = typer.Option(False, '--json', help='Output as JSON.'),
):
    """List all CloudFront distributions in the account."""
    dists = CloudFront__AWS__Client().list_distributions()
    if as_json:
        typer.echo(json.dumps([d.json() for d in dists], indent=2))
        return
    if not dists:
        console.print('No CloudFront distributions found.')
        return
    tbl = Table(title='CloudFront Distributions')
    tbl.add_column('ID',          style='cyan')
    tbl.add_column('Domain',      style='green')
    tbl.add_column('Status',      style='yellow')
    tbl.add_column('Enabled',     style='white')
    tbl.add_column('Aliases',     style='blue')
    tbl.add_column('Comment',     style='dim')
    for d in dists:
        tbl.add_row(
            str(d.distribution_id),
            str(d.domain_name),
            str(d.status),
            str(d.enabled),
            ', '.join(d.aliases) if d.aliases else '',
            d.comment,
        )
    console.print(tbl)


# ── distribution show ─────────────────────────────────────────────────────────

@distribution_app.command('show')
@spec_cli_errors
def distribution_show(
    distribution_id: str = typer.Argument(..., help='CloudFront distribution ID.'),
    as_json: bool        = typer.Option(False, '--json', help='Output as JSON.'),
):
    """Show details of a single CloudFront distribution."""
    dist = CloudFront__AWS__Client().get_distribution(distribution_id)
    if as_json:
        typer.echo(json.dumps(dist.json(), indent=2))
        return
    console.print(f'[cyan]ID:[/cyan]       {dist.distribution_id}')
    console.print(f'[cyan]Domain:[/cyan]   {dist.domain_name}')
    console.print(f'[cyan]Status:[/cyan]   {dist.status}')
    console.print(f'[cyan]Enabled:[/cyan]  {dist.enabled}')
    console.print(f'[cyan]Aliases:[/cyan]  {", ".join(dist.aliases) or "(none)"}')
    console.print(f'[cyan]CertARN:[/cyan]  {dist.cert_arn or "(default)"}')
    console.print(f'[cyan]Comment:[/cyan]  {dist.comment or "(none)"}')


# ── distribution create ───────────────────────────────────────────────────────

@distribution_app.command('create')
@spec_cli_errors
def distribution_create(
    origin_fn_url: str          = typer.Option(...,  '--origin-fn-url', help='Lambda Function URL (full URL or hostname).'),
    cert_arn:      str          = typer.Option(...,  '--cert-arn',      help='ACM certificate ARN (us-east-1).'),
    aliases:       Optional[str]= typer.Option(None, '--aliases',       help='Comma-separated CNAME aliases.'),
    comment:       str          = typer.Option('',   '--comment',       help='Human-readable distribution comment.'),
    price_class:   str          = typer.Option('PriceClass_All', '--price-class', help='CloudFront price class.'),
    as_json:       bool         = typer.Option(False, '--json',         help='Output as JSON.'),
):
    """Create a new CloudFront distribution pointing at a Lambda Function URL."""
    _mutation_guard()
    hostname = origin_fn_url.removeprefix('https://').removeprefix('http://').rstrip('/')
    alias_list = [a.strip() for a in aliases.split(',')] if aliases else []
    from sgraph_ai_service_playwright__cli.aws.cf.enums.Enum__CF__Price__Class import Enum__CF__Price__Class
    try:
        pc = Enum__CF__Price__Class(price_class)
    except ValueError:
        console.print(f'[red]Unknown price class: {price_class}[/red]')
        raise typer.Exit(1)
    req = Schema__CF__Create__Request(
        origin_domain = Safe_Str__CF__Domain_Name(hostname),
        cert_arn      = Safe_Str__Cert__Arn(cert_arn),
        aliases       = alias_list,
        comment       = comment,
        price_class   = pc,
    )
    resp = CloudFront__AWS__Client().create_distribution(req)
    if as_json:
        typer.echo(json.dumps(resp.json(), indent=2))
        return
    console.print(f'[green]Created[/green] {resp.distribution_id}')
    console.print(f'  Domain:  {resp.domain_name}')
    console.print(f'  Status:  {resp.status}')
    console.print('[dim]Distribution takes ~15 min to reach Deployed state.[/dim]')


# ── distribution disable ──────────────────────────────────────────────────────

@distribution_app.command('disable')
@spec_cli_errors
def distribution_disable(
    distribution_id: str = typer.Argument(..., help='CloudFront distribution ID.'),
    as_json: bool        = typer.Option(False, '--json', help='Output as JSON.'),
):
    """Disable a CloudFront distribution (required before deletion)."""
    _mutation_guard()
    resp = CloudFront__AWS__Client().disable_distribution(distribution_id)
    if as_json:
        typer.echo(json.dumps(resp.json(), indent=2))
        return
    if resp.success:
        console.print(f'[green]Disabled[/green] {distribution_id}')
        console.print('[dim]Wait for Deployed status before deleting.[/dim]')
    else:
        console.print(f'[red]Failed:[/red] {resp.message}')
        raise typer.Exit(1)


# ── distribution delete ───────────────────────────────────────────────────────

@distribution_app.command('delete')
@spec_cli_errors
def distribution_delete(
    distribution_id: str = typer.Argument(..., help='CloudFront distribution ID.'),
    as_json: bool        = typer.Option(False, '--json', help='Output as JSON.'),
):
    """Delete a disabled CloudFront distribution."""
    _mutation_guard()
    resp = CloudFront__AWS__Client().delete_distribution(distribution_id)
    if as_json:
        typer.echo(json.dumps(resp.json(), indent=2))
        return
    if resp.success:
        console.print(f'[green]Deleted[/green] {distribution_id}')
    else:
        console.print(f'[red]Failed:[/red] {resp.message}')
        raise typer.Exit(1)


# ── distribution wait ─────────────────────────────────────────────────────────

@distribution_app.command('wait')
@spec_cli_errors
def distribution_wait(
    distribution_id: str = typer.Argument(..., help='CloudFront distribution ID.'),
    timeout:         int = typer.Option(900,  '--timeout', help='Max wait time in seconds.'),
    as_json:         bool= typer.Option(False, '--json',   help='Output as JSON.'),
):
    """Wait until a CloudFront distribution reaches Deployed state."""
    console.print(f'Waiting for {distribution_id} to reach Deployed…')
    resp = CloudFront__AWS__Client().wait_deployed(distribution_id, timeout_sec=timeout)
    if as_json:
        typer.echo(json.dumps(resp.json(), indent=2))
        return
    if resp.success:
        console.print(f'[green]Deployed[/green] {distribution_id}')
    else:
        console.print(f'[red]{resp.message}[/red]')
        raise typer.Exit(1)
