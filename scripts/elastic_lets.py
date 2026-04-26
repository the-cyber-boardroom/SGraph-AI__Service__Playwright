# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — `sp el lets cf inventory ...` Typer surface
# Three-level command tree under the existing `sp el` (Elastic) app:
#   sp el lets                 — top-level LETS namespace (Load, Extract, Transform, Save)
#   sp el lets cf              — CloudFront real-time source
#   sp el lets cf inventory    — listing-metadata-only use case (no .gz reads)
#
# Slice 1 ships one verb (load).  Wipe + read verbs land in Phases 4 and 6.
#
# CLI commands here are thin: parse flags → resolve stack info via the
# existing Elastic__Service helpers → delegate to Inventory__Loader.load() →
# render the response with Rich.  All real logic lives in the
# sgraph_ai_service_playwright__cli/elastic/lets/cf/inventory/ package.
# ═══════════════════════════════════════════════════════════════════════════════

import os
from typing                                                                         import Optional

import typer
from rich.console                                                                   import Console
from rich.table                                                                     import Table

from sgraph_ai_service_playwright__cli.elastic.primitives.Safe_Str__Elastic__Stack__Name import Safe_Str__Elastic__Stack__Name
from sgraph_ai_service_playwright__cli.elastic.service.Kibana__Saved_Objects__Client     import Kibana__Saved_Objects__Client
from sgraph_ai_service_playwright__cli.observability.primitives.Safe_Str__AWS__Region    import Safe_Str__AWS__Region

from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket   import Safe_Str__S3__Bucket
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Key__Prefix import Safe_Str__S3__Key__Prefix
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.schemas.Schema__Inventory__Load__Request import Schema__Inventory__Load__Request
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__HTTP__Client import Inventory__HTTP__Client
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__Loader      import Inventory__Loader
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Run__Id__Generator    import Run__Id__Generator
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister import S3__Inventory__Lister


# ───────────────────────────────────────────────────────────────────────────────
# Typer app composition (registered onto the parent `sp el` app from scripts/elastic.py)
# ───────────────────────────────────────────────────────────────────────────────

app           = typer.Typer(help = 'LETS pipelines (Load, Extract, Transform, Save) on the ephemeral Kibana stack.',
                            no_args_is_help = True)
cf_app        = typer.Typer(help = 'CloudFront real-time logs LETS pipelines.',
                            no_args_is_help = True)
inventory_app = typer.Typer(help = 'S3 listing-metadata inventory for the CloudFront-realtime bucket. No .gz content reads in slice 1.',
                            no_args_is_help = True)

app.add_typer(cf_app, name='cf')
cf_app.add_typer(inventory_app, name='inventory')


def build_inventory_loader() -> Inventory__Loader:                                  # Single construction site so tests and CLI share the wiring
    return Inventory__Loader(s3_lister     = S3__Inventory__Lister()        ,
                              http_client   = Inventory__HTTP__Client()       ,
                              kibana_client = Kibana__Saved_Objects__Client() ,
                              run_id_gen    = Run__Id__Generator()            )


# ───────────────────────────────────────────────────────────────────────────────
# `sp el lets cf inventory load` — the only verb in slice 1
# ───────────────────────────────────────────────────────────────────────────────

@inventory_app.command('load')
def cmd_inventory_load(stack_name : Optional[str] = typer.Argument(None,                       help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
                       bucket     : Optional[str] = typer.Option  (None, '--bucket',           help='S3 bucket holding the CloudFront-realtime objects (defaults to the SGraph CloudFront-logs bucket).'),
                       prefix     : Optional[str] = typer.Option  (None, '--prefix',           help='S3 key prefix (e.g. "cloudfront-realtime/2026/04/25/"). Empty + no --all defaults to today UTC.'),
                       all_objects: bool          = typer.Option  (False, '--all',             help='List the entire bucket (slow; for the "eventually all of it" path). Ignored when --prefix is set.'),
                       max_keys   : int           = typer.Option  (0,    '--max-keys',         help='Stop after N objects. 0 (default) = unlimited.'),
                       run_id     : Optional[str] = typer.Option  (None, '--run-id',           help='Pipeline run id. Empty = service auto-generates.'),
                       password   : Optional[str] = typer.Option  (None, '--password',         help='Elastic password (else $SG_ELASTIC_PASSWORD).'),
                       region     : Optional[str] = typer.Option  (None, '--region',           help='AWS region (defaults to current AWS_Config session region).'),
                       dry_run    : bool          = typer.Option  (False, '--dry-run',         help='List + parse only; skip the bulk-post into Elastic.')):
    """Load CloudFront S3 listing metadata into the ephemeral Kibana stack (sg-cf-inventory-* index)."""
    # Imported here (not at module top) to avoid a circular import: scripts.elastic
    # imports this module to mount the lets sub-app.
    from scripts.elastic                                                             import build_service, resolve_stack_name, aws_error_handler, rich_escape

    @aws_error_handler
    def _run():
        c = Console(highlight=False)

        # Pre-flight: password must be available before we touch AWS / HTTP
        if not dry_run and not password and not os.environ.get('SG_ELASTIC_PASSWORD'):
            c.print('\n  [yellow]⚠[/]  SG_ELASTIC_PASSWORD is not set.')
            c.print('     [dim]Re-export it from the most recent `sp elastic create` output, e.g.:[/]')
            c.print('     [bold]export SG_ELASTIC_PASSWORD=<password-from-create>[/]')
            c.print('     [dim]Or pass it explicitly via --password.[/]\n')
            raise typer.Exit(1)

        service       = build_service()
        stack_picked  = resolve_stack_name(service, stack_name, region)
        info          = service.get_stack_info(stack_name = Safe_Str__Elastic__Stack__Name(stack_picked),
                                                region     = region or '')
        if not str(info.kibana_url):
            c.print(f'\n  [red]✗  Stack [bold]{stack_picked}[/] has no Kibana URL yet.[/]  Run `sp el wait` first.\n')
            raise typer.Exit(1)

        base_url      = str(info.kibana_url).rstrip('/')
        elastic_pwd   = password or os.environ.get('SG_ELASTIC_PASSWORD', '')
        request       = Schema__Inventory__Load__Request(stack_name = Safe_Str__Elastic__Stack__Name(stack_picked) ,
                                                          bucket     = Safe_Str__S3__Bucket(bucket or '')           ,
                                                          prefix     = Safe_Str__S3__Key__Prefix(prefix or '')      ,
                                                          all        = bool(all_objects)                             ,
                                                          max_keys   = int(max_keys)                                 ,
                                                          run_id     = Safe_Str__Pipeline__Run__Id(run_id or '')     ,
                                                          region     = Safe_Str__AWS__Region(region or '')           ,    # Empty → boto3 falls through to AWS_DEFAULT_REGION
                                                          dry_run    = bool(dry_run)                                 )

        loader        = build_inventory_loader()
        import time as _time
        t0            = _time.time()
        response      = loader.load(request  = request    ,
                                     base_url = base_url   ,
                                     username = 'elastic'  ,
                                     password = elastic_pwd)
        wall_ms       = int((_time.time() - t0) * 1000)

        # ─── render summary ─────────────────────────────────────────────────
        c.print()
        title_suffix = '  [yellow](dry-run)[/]' if response.dry_run else ''
        c.print(f'  [bold]CloudFront inventory load[/]{title_suffix}')
        c.print()
        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column(style='dim', justify='right')
        t.add_column(style='bold')
        t.add_row('stack'           , str(response.stack_name      ))
        t.add_row('run-id'          , str(response.run_id          ))
        t.add_row('bucket'          , str(response.bucket          ))
        t.add_row('prefix'          , str(response.prefix_resolved ) or '[dim](full bucket)[/]')
        t.add_row('pages-listed'    , str(response.pages_listed    ))
        t.add_row('objects-scanned' , str(response.objects_scanned ))
        if not response.dry_run:
            t.add_row('objects-indexed', str(response.objects_indexed))
            t.add_row('objects-updated', str(response.objects_updated))
        t.add_row('bytes-total'     , f'{response.bytes_total:,}')
        t.add_row('wall-time'       , f'{wall_ms} ms')
        if not response.dry_run:
            t.add_row('http-status' , str(response.last_http_status))
            t.add_row('kibana-url'  , str(response.kibana_url      ))
        c.print(t)

        if str(response.error_message):                                              # Surface failures the same way `sp el seed` does — escape user-controlled body
            c.print()
            c.print(f'  [red]✗[/]  {rich_escape(str(response.error_message))}')
            if response.last_http_status == 401 or response.last_http_status == 403:
                c.print('     [dim]› Likely SG_ELASTIC_PASSWORD does not match the live stack — re-export from `sp el create`.[/]')

        if not response.dry_run and response.objects_indexed + response.objects_updated > 0:
            c.print()
            c.print(f'  [green]✓[/]  Open Kibana Discover at [bold]{base_url}/app/discover[/]')

        c.print()

    _run()
