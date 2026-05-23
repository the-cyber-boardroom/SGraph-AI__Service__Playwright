# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Sentinel__Deploy
# `sg sentinel deploy *` — the live AWS path (Target A). Mutation-gated.
#
#   sg sentinel deploy create   [--distribution ID] [--region R] [--bucket B] [--yes] [--dry-run]
#   sg sentinel deploy destroy  <distribution-id>                                  [--yes] [--dry-run]
#   sg sentinel deploy teardown <distribution-id> [--bucket B]                     [--yes] [--dry-run]
#
# create provisions the CF Function (L1, viewer-request) + Lambda@Edge (L2,
# origin-request) on a cache-disabled distribution writing to an S3 log bucket.
# teardown removes everything incl. the bucket (no orphans).
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console

from sgraph_ai_service_playwright__cli.aws._shared.Aws__Confirm                       import confirm_or_abort
from sgraph_ai_service_playwright__cli.aws._shared.Aws__Context__Banner               import Aws__Context__Banner
from sgraph_ai_service_playwright__cli.aws._shared.Mutation__Gate                     import require_mutation_gate
from sgraph_ai_service_playwright__cli.aws._shared.auth.AWS__Auth__Guard              import aws_auth_guard
from sgraph_ai_service_playwright__cli.sentinel.schemas.Schema__Sentinel__Deploy__Request import Schema__Sentinel__Deploy__Request
from sgraph_ai_service_playwright__cli.sentinel.service.Sentinel__Deployer            import Sentinel__Deployer
from sg_compute.cli.base.Spec__CLI__Errors                                           import spec_cli_errors

app     = typer.Typer(name='deploy', help='Live AWS deploy (create / destroy / teardown). Mutation-gated.', no_args_is_help=True)
console = Console()

_MUTATION_ENV = 'SG_AWS__SENTINEL__ALLOW_MUTATIONS'


def _deployer(region: str) -> Sentinel__Deployer:
    banner  = Aws__Context__Banner().resolve(region)
    account = banner.get('account_id', '')
    return Sentinel__Deployer(region=region or 'us-east-1', account_id=account)


@app.command('create')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
@aws_auth_guard(family='sentinel')
def cmd_create(distribution : str  = typer.Option('', '--distribution', help='Existing distribution id, or empty to create a new ephemeral one.'),
               region       : str  = typer.Option('', '--region',       help='AWS region (default us-east-1).'),
               bucket       : str  = typer.Option('', '--bucket',       help='Log bucket name, or empty to derive one.'),
               yes          : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation.'),
               dry_run      : bool = typer.Option(False, '--dry-run',   help='Print the intended action without executing.')):
    """Provision the SG/Sentinel live stack (CF Function + Lambda@Edge + S3 log bucket)."""
    console.print(Aws__Context__Banner().render(region))
    if dry_run:
        console.print(f'[dim](dry-run)[/dim] would create: CF Function + Lambda@Edge + log bucket '
                      f'(distribution={distribution or "new"}, region={region or "us-east-1"}, bucket={bucket or "derived"})')
        return
    if not confirm_or_abort('Create the SG/Sentinel live stack?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)
    req  = Schema__Sentinel__Deploy__Request(distribution_id=distribution, region=region or 'us-east-1', log_bucket=bucket)
    resp = _deployer(region).create(req)
    console.print(f'[green]created[/green]  distribution={resp.distribution_id}  bucket={resp.log_bucket}')
    console.print(f'  L1 (CF Function): {resp.cf_function_arn}')
    console.print(f'  L2 (Lambda@Edge): {resp.lambda_edge_arn}')


@app.command('destroy')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
@aws_auth_guard(family='sentinel')
def cmd_destroy(distribution : str  = typer.Argument(..., help='Distribution id to destroy.'),
                region       : str  = typer.Option('', '--region', help='AWS region.'),
                yes          : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation.'),
                dry_run      : bool = typer.Option(False, '--dry-run', help='Print the intended action without executing.')):
    """Remove the distribution + CF Function + Lambda@Edge (keeps the log bucket)."""
    console.print(Aws__Context__Banner().render(region))
    if dry_run:
        console.print(f'[dim](dry-run)[/dim] would destroy distribution {distribution} + edge resources')
        return
    if not confirm_or_abort(f'Destroy distribution {distribution} + edge resources?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)
    resp = _deployer(region).destroy(distribution)
    console.print(f'[green]{resp.status}[/green]  distribution={resp.distribution_id}')


@app.command('teardown')
@spec_cli_errors
@require_mutation_gate(_MUTATION_ENV)
@aws_auth_guard(family='sentinel')
def cmd_teardown(distribution : str  = typer.Argument(..., help='Distribution id to tear down.'),
                 bucket       : str  = typer.Option('', '--bucket', help='Log bucket to empty + delete (no orphans).'),
                 region       : str  = typer.Option('', '--region', help='AWS region.'),
                 yes          : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation.'),
                 dry_run      : bool = typer.Option(False, '--dry-run', help='Print the intended action without executing.')):
    """Remove everything incl. the log bucket — no orphans."""
    console.print(Aws__Context__Banner().render(region))
    if dry_run:
        console.print(f'[dim](dry-run)[/dim] would tear down distribution {distribution} + bucket {bucket or "(none)"}')
        return
    if not confirm_or_abort(f'Tear down distribution {distribution} and bucket {bucket or "(none)"}?', yes=yes, dry_run=dry_run):
        raise typer.Exit(0)
    resp = _deployer(region).teardown(distribution, log_bucket=bucket)
    console.print(f'[green]{resp.status}[/green]  distribution={resp.distribution_id}  bucket={resp.log_bucket}')
