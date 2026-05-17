# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vault-publish: Cli__Vault_Publish
# Typer app for `sg vp` / `sg vault-publish` commands.
#   register  : publish a vault-app stack under a slug + FQDN
#   unpublish : remove slug, stack, and DNS record
#   status    : show EC2 state + FQDN for a slug
#   list      : list all registered slugs (vault keys redacted)
#   bootstrap : Phase 2d stub — prints PROPOSED and exits non-zero
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import time
from typing import Optional

import typer
from rich.console import Console
from rich.table   import Table

from sg_compute.cli.base.Spec__CLI__Defaults                              import DEFAULT_REGION
from sg_compute_specs.vault_publish.schemas.Safe_Str__Slug                import Safe_Str__Slug
from sg_compute_specs.vault_publish.schemas.Safe_Str__Vault__Key          import Safe_Str__Vault__Key
from sg_compute_specs.vault_publish.schemas.Schema__Vault_Publish__Register__Request import Schema__Vault_Publish__Register__Request
from sg_compute_specs.vault_publish.service.Vault_Publish__Service        import Vault_Publish__Service

app = typer.Typer(name='vault-publish', help='Vault Publish — subdomain-routing for vault-app stacks.', no_args_is_help=True)


def _svc() -> Vault_Publish__Service:
    return Vault_Publish__Service().setup()


@app.command(name='register', help='Publish a vault-app stack at <slug>.aws.sg-labs.app.')
def register(slug     : str = typer.Argument(..., help='DNS slug (e.g. sara-cv)'),
             vault_key: str = typer.Option(..., '--vault-key', '-k', help='Vault key identifier'),
             region   : str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    c   = Console(highlight=False)
    req = Schema__Vault_Publish__Register__Request(
        slug      = Safe_Str__Slug(slug),
        vault_key = Safe_Str__Vault__Key(vault_key),
        region    = region)
    c.print(f'\n  [yellow]→[/]  Registering [bold]{slug}[/]…')
    resp = _svc().register(req)
    if not str(getattr(resp, 'fqdn', '')):
        c.print(f'  [red]✗  {resp.message}[/]')
        raise typer.Exit(1)
    c.print(f'  [green]✓[/]  Registered [bold]{slug}[/]')
    c.print(f'      FQDN      : {resp.fqdn}')
    c.print(f'      Stack     : {resp.stack_name}')
    c.print(f'      elapsed   : {resp.elapsed_ms}ms')
    c.print()


@app.command(name='unpublish', help='Remove a slug, its stack, and its DNS record.')
def unpublish(slug  : str  = typer.Argument(..., help='Slug to unpublish'),
              region: str  = typer.Option(DEFAULT_REGION, '--region', '-r'),
              yes   : bool = typer.Option(False, '--yes', '-y', help='Skip confirmation')):
    c = Console(highlight=False)
    if not yes:
        typer.confirm(f"\n  Delete slug '{slug}' and its vault-app stack?", default=True, abort=True)
    c.print(f'\n  [yellow]→[/]  Unpublishing [bold]{slug}[/]…')
    resp = _svc().unpublish(slug)
    if not getattr(resp, 'deleted', False):
        c.print(f'  [red]✗  {resp.message}[/]')
        raise typer.Exit(1)
    c.print(f'  [green]✓[/]  Unpublished [bold]{slug}[/]  (stack: {resp.stack_name})')
    c.print()


@app.command(name='status', help='Show EC2 state and FQDN for a registered slug.')
def status(slug  : str = typer.Argument(..., help='Slug to query'),
           region: str = typer.Option(DEFAULT_REGION, '--region', '-r')):
    c    = Console(highlight=False)
    resp = _svc().status(slug)
    c.print()
    c.print(f'  Slug  : {slug}')
    c.print(f'  State : {resp.state}')
    c.print(f'  FQDN  : {resp.fqdn}')
    if getattr(resp, 'vault_url', ''):
        c.print(f'  URL   : {resp.vault_url}')
    if getattr(resp, 'public_ip', ''):
        c.print(f'  IP    : {resp.public_ip}')
    c.print()


@app.command(name='list', help='List all registered slugs (vault keys redacted).')
def list_slugs():
    c    = Console(highlight=False)
    resp = _svc().list_slugs()
    if not resp.total:
        c.print('\n  (no slugs registered)\n')
        return
    tbl = Table(box=None, show_header=True, padding=(0, 2))
    tbl.add_column('Slug',       style='bold')
    tbl.add_column('FQDN',       style='cyan')
    tbl.add_column('Stack',      style='dim')
    tbl.add_column('Region',     style='dim')
    tbl.add_column('Created',    style='dim')
    for entry in resp.entries:
        tbl.add_row(str(entry.slug), str(entry.fqdn), str(entry.stack_name),
                    str(entry.region), str(entry.created_at))
    c.print()
    c.print(tbl)
    c.print(f'\n  Total: {resp.total}\n')


@app.command(name='bootstrap', help='[PROPOSED] Bootstrap CloudFront + Waker Lambda. Lands in Phase 2d.')
def bootstrap():
    c = Console(highlight=False)
    c.print('\n  [yellow]⚠[/]  PROPOSED — does not exist yet. Land in phase 2d.\n')
    raise typer.Exit(2)
