# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Cli__Acm
# Typer CLI surface for ACM certificate management. Read-only (P0).
# All commands delegate to ACM__AWS__Client — no boto3 here.
#
# Command tree:
#   sg aws acm list   [--region <name>] [--all-regions] [--json]
#   sg aws acm show   <arn-or-domain>   [--region <name>] [--json]
#
# Default for list: dual-region (current region + us-east-1) because
# CloudFront certificates must live in us-east-1.
# ═══════════════════════════════════════════════════════════════════════════════

import json

import typer
from rich.console import Console
from rich.table   import Table

from sgraph_ai_service_playwright__cli.aws.acm.service.ACM__AWS__Client            import ACM__AWS__Client

acm_app = typer.Typer(name='acm', help='ACM certificate management (read-only).', no_args_is_help=True)


def _client() -> ACM__AWS__Client:
    return ACM__AWS__Client()


def _arn_short(arn: str) -> str:                                                     # Returns last 8 hex chars of the certificate UUID for compact table display
    parts = arn.split('/')
    uuid  = parts[-1] if parts else arn
    return f'…/{uuid[-8:]}' if len(uuid) > 8 else uuid


# ── acm list ──────────────────────────────────────────────────────────────────

@acm_app.command('list')
def acm_list(region     : str  = typer.Option(None,  '--region',      '-r', help='AWS region. Omit for dual-region scan (current + us-east-1).'),
             all_regions: bool = typer.Option(False, '--all-regions',       help='Scan all commercial regions (slow; rate-limited).'),
             json_output: bool = typer.Option(False, '--json',              help='Output JSON instead of a table.')):
    """List ACM certificates. Default: current region + us-east-1 (dual-region)."""
    client = _client()
    if all_regions:
        typer.echo('[yellow]--all-regions is not implemented in P0; use --region or dual-region default.[/]', err=True)
        raise typer.Exit(1)
    if region:
        certs = client.list_certificates(region=region)
    else:
        certs = client.list_certificates__dual_region()
    if json_output:
        typer.echo(json.dumps([dict(arn             = c.arn                       ,
                                    domain_name     = str(c.domain_name)          ,
                                    san_count       = c.san_count                 ,
                                    status          = str(c.status)               ,
                                    cert_type       = str(c.cert_type)            ,
                                    in_use_by       = c.in_use_by                 ,
                                    renewal_eligible= c.renewal_eligible          ,
                                    region          = c.region                    )
                                for c in certs], indent=2))
        return
    c = Console(highlight=False)
    c.print()
    c.print(f'  ACM certificates  ·  {len(certs)} certs')
    c.print()
    t = Table(box=None, show_header=True, padding=(0, 2))
    t.add_column('ARN (short)',  style='dim',   min_width=14, no_wrap=True)
    t.add_column('Region',       style='',      min_width=10, no_wrap=True)
    t.add_column('Domain',       style='bold',  min_width=20)
    t.add_column('SANs',         style='',      min_width=4)
    t.add_column('Status',       style='cyan',  min_width=8)
    t.add_column('Type',         style='',      min_width=13)
    t.add_column('In-Use-By',    style='',      min_width=9)
    t.add_column('Renewal',      style='',      min_width=6)
    for cert in certs:
        renewal = 'ELIGIBLE' if cert.renewal_eligible else '—'
        t.add_row(_arn_short(cert.arn), cert.region, str(cert.domain_name),
                  str(cert.san_count), str(cert.status), str(cert.cert_type),
                  str(cert.in_use_by), renewal)
    c.print(t)
    c.print()


# ── acm show ──────────────────────────────────────────────────────────────────

@acm_app.command('show')
def acm_show(arn_or_domain: str  = typer.Argument(..., help='Full ACM certificate ARN.'),
             region       : str  = typer.Option(None,  '--region', '-r', help='AWS region. Auto-detected from ARN when omitted.'),
             json_output  : bool = typer.Option(False, '--json',         help='Output JSON instead of a table.')):
    """Show details of one ACM certificate (pass the full ARN)."""
    client = _client()
    cert   = client.describe_certificate(arn_or_domain, region=region)
    if cert is None:
        typer.echo(f'Certificate not found: {arn_or_domain}', err=True)
        raise typer.Exit(1)
    if json_output:
        typer.echo(json.dumps(dict(arn             = cert.arn                    ,
                                   domain_name     = str(cert.domain_name)       ,
                                   san_count       = cert.san_count              ,
                                   status          = str(cert.status)            ,
                                   cert_type       = str(cert.cert_type)         ,
                                   in_use_by       = cert.in_use_by              ,
                                   renewal_eligible= cert.renewal_eligible       ,
                                   region          = cert.region                 ), indent=2))
        return
    c = Console(highlight=False)
    c.print()
    t = Table(box=None, show_header=False, padding=(0, 2))
    t.add_column(style='bold', min_width=18, no_wrap=True)
    t.add_column()
    renewal = 'ELIGIBLE' if cert.renewal_eligible else 'INELIGIBLE'
    t.add_row('arn',             cert.arn)
    t.add_row('region',          cert.region)
    t.add_row('domain',          str(cert.domain_name))
    t.add_row('san-count',       str(cert.san_count))
    t.add_row('status',          str(cert.status))
    t.add_row('type',            str(cert.cert_type))
    t.add_row('in-use-by',       str(cert.in_use_by))
    t.add_row('renewal',         renewal)
    c.print(t)
    c.print()
