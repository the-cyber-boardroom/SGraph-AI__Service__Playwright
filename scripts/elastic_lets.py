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
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__Read        import Inventory__Read
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Inventory__Wiper       import Inventory__Wiper
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.Run__Id__Generator    import Run__Id__Generator
from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.service.S3__Inventory__Lister import S3__Inventory__Lister

# Slice 2 — events:
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.schemas.Schema__Events__Load__Request import Schema__Events__Load__Request
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Bot__Classifier            import Bot__Classifier
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.CF__Realtime__Log__Parser import CF__Realtime__Log__Parser
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Events__Loader              import Events__Loader
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Events__Wiper                import Events__Wiper
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Reader  import Inventory__Manifest__Reader
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Updater import Inventory__Manifest__Updater
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.S3__Object__Fetcher          import S3__Object__Fetcher


# ───────────────────────────────────────────────────────────────────────────────
# Typer app composition (registered onto the parent `sp el` app from scripts/elastic.py)
# ───────────────────────────────────────────────────────────────────────────────

app           = typer.Typer(help = 'LETS pipelines (Load, Extract, Transform, Save) on the ephemeral Kibana stack.',
                            no_args_is_help = True)
cf_app        = typer.Typer(help = 'CloudFront real-time logs LETS pipelines.',
                            no_args_is_help = True)
inventory_app = typer.Typer(help = 'S3 listing-metadata inventory for the CloudFront-realtime bucket. No .gz content reads in slice 1.',
                            no_args_is_help = True)
events_app    = typer.Typer(help = 'CloudFront real-time log EVENTS — fetches each .gz, parses the TSV into typed records, indexes to sg-cf-events-*.',
                            no_args_is_help = True)

app.add_typer(cf_app, name='cf')
cf_app.add_typer(inventory_app, name='inventory')
cf_app.add_typer(events_app   , name='events')


def build_inventory_loader() -> Inventory__Loader:                                  # Single construction site so tests and CLI share the wiring
    return Inventory__Loader(s3_lister     = S3__Inventory__Lister()        ,
                              http_client   = Inventory__HTTP__Client()       ,
                              kibana_client = Kibana__Saved_Objects__Client() ,
                              run_id_gen    = Run__Id__Generator()            )


def build_inventory_wiper() -> Inventory__Wiper:
    return Inventory__Wiper(http_client   = Inventory__HTTP__Client()       ,
                             kibana_client = Kibana__Saved_Objects__Client() )


def build_inventory_read() -> Inventory__Read:
    return Inventory__Read(http_client   = Inventory__HTTP__Client()       ,
                            kibana_client = Kibana__Saved_Objects__Client() )


def build_events_loader() -> Events__Loader:                                        # Composition root for the events pipeline (slice 2)
    return Events__Loader(s3_lister        = S3__Inventory__Lister()                                    ,
                           s3_fetcher       = S3__Object__Fetcher()                                      ,
                           parser           = CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier()),
                           http_client      = Inventory__HTTP__Client()                                  ,
                           kibana_client    = Kibana__Saved_Objects__Client()                            ,
                           manifest_reader  = Inventory__Manifest__Reader (http_client=Inventory__HTTP__Client()),
                           manifest_updater = Inventory__Manifest__Updater(http_client=Inventory__HTTP__Client()),
                           run_id_gen       = Run__Id__Generator()                                        )


def build_events_wiper() -> Events__Wiper:
    return Events__Wiper(http_client      = Inventory__HTTP__Client()                                    ,
                          kibana_client    = Kibana__Saved_Objects__Client()                              ,
                          manifest_updater = Inventory__Manifest__Updater(http_client=Inventory__HTTP__Client()))


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


# ───────────────────────────────────────────────────────────────────────────────
# `sp el lets cf inventory wipe` — the matched pair to load
# ───────────────────────────────────────────────────────────────────────────────

@inventory_app.command('wipe')
def cmd_inventory_wipe(stack_name : Optional[str] = typer.Argument(None,                  help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
                       password   : Optional[str] = typer.Option  (None, '--password',    help='Elastic password (else $SG_ELASTIC_PASSWORD).'),
                       region     : Optional[str] = typer.Option  (None, '--region',      help='AWS region (defaults to current AWS_Config session region).'),
                       yes        : bool          = typer.Option  (False, '--yes', '-y',  help='Skip the y/N confirmation prompt.')):
    """Drop every sg-cf-inventory-* index, both data view titles, and the dashboard saved-objects. Idempotent: a second wipe returns all-zeros."""
    from scripts.elastic                                                             import build_service, resolve_stack_name, aws_error_handler, rich_escape

    @aws_error_handler
    def _run():
        c = Console(highlight=False)

        if not password and not os.environ.get('SG_ELASTIC_PASSWORD'):
            c.print('\n  [yellow]⚠[/]  SG_ELASTIC_PASSWORD is not set.')
            c.print('     [dim]Re-export it from the most recent `sp elastic create` output, or pass --password.[/]\n')
            raise typer.Exit(1)

        service       = build_service()
        stack_picked  = resolve_stack_name(service, stack_name, region)
        info          = service.get_stack_info(stack_name = Safe_Str__Elastic__Stack__Name(stack_picked),
                                                region     = region or '')
        if not str(info.kibana_url):
            c.print(f'\n  [red]✗  Stack [bold]{stack_picked}[/] has no Kibana URL yet.[/]\n')
            raise typer.Exit(1)

        if not yes:
            c.print(f'\n  [yellow]About to wipe all CloudFront-inventory data on [bold]{stack_picked}[/]:[/]')
            c.print('    [dim]·[/] every [bold]sg-cf-inventory-*[/] index')
            c.print('    [dim]·[/] both data views ([bold]sg-cf-inventory-*[/], legacy [bold]sg-cf-inventory[/])')
            c.print('    [dim]·[/] the [bold]CloudFront Logs - Inventory Overview[/] dashboard + visualisations')
            if not typer.confirm('\n  Proceed?', default=False):
                c.print('  [dim]aborted[/]\n')
                raise typer.Exit(0)

        base_url    = str(info.kibana_url).rstrip('/')
        elastic_pwd = password or os.environ.get('SG_ELASTIC_PASSWORD', '')
        wiper       = build_inventory_wiper()
        response    = wiper.wipe(base_url   = base_url                                            ,
                                  username   = 'elastic'                                           ,
                                  password   = elastic_pwd                                         ,
                                  stack_name = Safe_Str__Elastic__Stack__Name(stack_picked)        )

        c.print()
        total_dropped = response.indices_dropped + response.data_views_dropped + response.saved_objects_dropped
        if total_dropped == 0:
            c.print(f'  [green]✓[/]  Already clean — nothing to wipe on [bold]{stack_picked}[/]')
        else:
            c.print(f'  [green]✓[/]  Wiped CloudFront inventory on [bold]{stack_picked}[/]')
        c.print()
        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column(style='dim', justify='right')
        t.add_column(style='bold')
        t.add_row('indices-dropped'      , str(response.indices_dropped      ))
        t.add_row('data-views-dropped'   , str(response.data_views_dropped   ))
        t.add_row('saved-objects-dropped', str(response.saved_objects_dropped))
        t.add_row('duration'             , f'{response.duration_ms} ms')
        c.print(t)

        if str(response.error_message):
            c.print()
            c.print(f'  [yellow]⚠[/]  {rich_escape(str(response.error_message))}')
        c.print()

    _run()


# ───────────────────────────────────────────────────────────────────────────────
# `sp el lets cf inventory list` — show distinct pipeline runs in Elastic
# ───────────────────────────────────────────────────────────────────────────────

@inventory_app.command('list')
def cmd_inventory_list(stack_name : Optional[str] = typer.Argument(None,                  help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
                       password   : Optional[str] = typer.Option  (None, '--password',    help='Elastic password (else $SG_ELASTIC_PASSWORD).'),
                       region     : Optional[str] = typer.Option  (None, '--region',      help='AWS region (defaults to current AWS_Config session region).'),
                       top_n      : int           = typer.Option  (100,  '--top',         help='Show at most N runs (default 100).')):
    """List distinct pipeline runs currently indexed in sg-cf-inventory-*. One row per pipeline_run_id."""
    from scripts.elastic                                                             import build_service, resolve_stack_name, aws_error_handler

    @aws_error_handler
    def _run():
        c = Console(highlight=False)
        if not password and not os.environ.get('SG_ELASTIC_PASSWORD'):
            c.print('\n  [yellow]⚠[/]  SG_ELASTIC_PASSWORD is not set.\n')
            raise typer.Exit(1)

        service       = build_service()
        stack_picked  = resolve_stack_name(service, stack_name, region)
        info          = service.get_stack_info(stack_name = Safe_Str__Elastic__Stack__Name(stack_picked),
                                                region     = region or '')
        if not str(info.kibana_url):
            c.print(f'\n  [red]✗  Stack [bold]{stack_picked}[/] has no Kibana URL yet.[/]\n')
            raise typer.Exit(1)

        base_url    = str(info.kibana_url).rstrip('/')
        elastic_pwd = password or os.environ.get('SG_ELASTIC_PASSWORD', '')
        reader      = build_inventory_read()
        runs        = reader.list_runs(base_url=base_url, username='elastic', password=elastic_pwd, top_n=top_n)

        c.print()
        if len(runs) == 0:
            c.print(f'  [dim]No runs in sg-cf-inventory-* on [bold]{stack_picked}[/].  Run `sp el lets cf inventory load`.[/]\n')
            return

        c.print(f'  [bold]Pipeline runs on [cyan]{stack_picked}[/cyan][/]')
        c.print()
        t = Table(show_header=True, header_style='bold', box=None, padding=(0, 2))
        t.add_column('Run id'   , style='dim'                   )
        t.add_column('Objects'  , justify='right'               )
        t.add_column('Bytes'    , justify='right'               )
        t.add_column('Delivery range'                           )
        t.add_column('Loaded at'                                )
        for run in runs:
            delivery_range = str(run.earliest_delivery)[:10]                          # YYYY-MM-DD
            if str(run.latest_delivery)[:10] != delivery_range:
                delivery_range = f'{delivery_range} → {str(run.latest_delivery)[:10]}'
            loaded_at = str(run.latest_loaded).replace('T', ' ').rstrip('Z').split('.')[0]
            t.add_row(str(run.pipeline_run_id),
                       str(run.object_count   ),
                       f'{int(run.bytes_total):,}',
                       delivery_range,
                       loaded_at)
        c.print(t)
        c.print(f'\n  [dim]{len(runs)} run(s)[/]\n')

    _run()


# ───────────────────────────────────────────────────────────────────────────────
# `sp el lets cf inventory health` — check that the dataset's plumbing is intact
# ───────────────────────────────────────────────────────────────────────────────

@inventory_app.command('health')
def cmd_inventory_health(stack_name : Optional[str] = typer.Argument(None,                help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
                          password   : Optional[str] = typer.Option  (None, '--password',  help='Elastic password (else $SG_ELASTIC_PASSWORD).'),
                          region     : Optional[str] = typer.Option  (None, '--region',    help='AWS region (defaults to current AWS_Config session region).')):
    """Check the inventory dataset's plumbing: indices, data view, dashboard. Mirrors `sp el health` style."""
    from scripts.elastic                                                             import build_service, resolve_stack_name, aws_error_handler, rich_escape

    @aws_error_handler
    def _run():
        c = Console(highlight=False)
        if not password and not os.environ.get('SG_ELASTIC_PASSWORD'):
            c.print('\n  [yellow]⚠[/]  SG_ELASTIC_PASSWORD is not set.\n')
            raise typer.Exit(1)

        service       = build_service()
        stack_picked  = resolve_stack_name(service, stack_name, region)
        info          = service.get_stack_info(stack_name = Safe_Str__Elastic__Stack__Name(stack_picked),
                                                region     = region or '')
        if not str(info.kibana_url):
            c.print(f'\n  [red]✗  Stack [bold]{stack_picked}[/] has no Kibana URL yet.[/]\n')
            raise typer.Exit(1)

        base_url    = str(info.kibana_url).rstrip('/')
        elastic_pwd = password or os.environ.get('SG_ELASTIC_PASSWORD', '')
        reader      = build_inventory_read()
        response    = reader.health(base_url=base_url, username='elastic', password=elastic_pwd,
                                     stack_name=Safe_Str__Elastic__Stack__Name(stack_picked))

        icon_for = {'ok': '[green]✓[/]', 'warn': '[yellow]⚠[/]', 'fail': '[red]✗[/]', 'skip': '[dim]·[/]'}
        has_warn    = any(str(chk.status) == 'warn' for chk in response.checks)
        rollup_icon = '[red]✗[/]' if not response.all_ok else ('[yellow]⚠[/]' if has_warn else '[green]✓[/]')
        c.print()
        c.print(f'  {rollup_icon}  Inventory health for [bold]{stack_picked}[/]')
        c.print()
        t = Table(show_header=True, header_style='bold', box=None, padding=(0, 2))
        t.add_column('', width=2)
        t.add_column('Check')
        t.add_column('Detail', style='dim')
        for chk in response.checks:
            t.add_row(icon_for.get(str(chk.status), '·'), str(chk.name), rich_escape(str(chk.detail)))
        c.print(t)
        c.print()

    _run()


# ───────────────────────────────────────────────────────────────────────────────
# `sp el lets cf events load` — fetch .gz files, parse TSV, index events
# ───────────────────────────────────────────────────────────────────────────────

@events_app.command('load')
def cmd_events_load(stack_name      : Optional[str] = typer.Argument(None,                       help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
                    bucket          : Optional[str] = typer.Option  (None, '--bucket',           help='S3 bucket holding the CloudFront-realtime objects (defaults to the SGraph CloudFront-logs bucket).'),
                    prefix          : Optional[str] = typer.Option  (None, '--prefix',           help='S3 key prefix (e.g. "cloudfront-realtime/2026/04/25/"). Empty + no --all + no --from-inventory defaults to today UTC.'),
                    all_objects     : bool          = typer.Option  (False, '--all',             help='Full-bucket scan (S3 listing mode). Ignored when --prefix is set.'),
                    max_files       : int           = typer.Option  (0,    '--max-files',        help='Stop after N FILES (NOT events). 0 = unlimited. With --from-inventory, defaults to 1000 (the manifest-reader top_n cap).'),
                    from_inventory  : bool          = typer.Option  (False, '--from-inventory',  help='Use the inventory manifest (sg-cf-inventory-* docs where content_processed=false) as the work queue. Pays off slice 1\'s content_processed forward declaration.'),
                    run_id          : Optional[str] = typer.Option  (None, '--run-id',           help='Pipeline run id. Empty = service auto-generates.'),
                    password        : Optional[str] = typer.Option  (None, '--password',         help='Elastic password (else $SG_ELASTIC_PASSWORD).'),
                    region          : Optional[str] = typer.Option  (None, '--region',           help='AWS region (defaults to current AWS_Config session region).'),
                    dry_run         : bool          = typer.Option  (False, '--dry-run',         help='Build the queue, skip the fetch + parse + bulk-post + manifest update.')):
    """Load CloudFront events into the ephemeral Kibana stack (sg-cf-events-* index family)."""
    from scripts.elastic                                                             import build_service, resolve_stack_name, aws_error_handler, rich_escape
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__Pipeline__Run__Id import Safe_Str__Pipeline__Run__Id
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket       import Safe_Str__S3__Bucket
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Key__Prefix  import Safe_Str__S3__Key__Prefix

    @aws_error_handler
    def _run():
        c = Console(highlight=False)

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

        base_url     = str(info.kibana_url).rstrip('/')
        elastic_pwd  = password or os.environ.get('SG_ELASTIC_PASSWORD', '')
        request      = Schema__Events__Load__Request(stack_name     = Safe_Str__Elastic__Stack__Name(stack_picked) ,
                                                      bucket         = Safe_Str__S3__Bucket(bucket or '')           ,
                                                      prefix         = Safe_Str__S3__Key__Prefix(prefix or '')      ,
                                                      all            = bool(all_objects)                             ,
                                                      max_files      = int(max_files)                                ,
                                                      from_inventory = bool(from_inventory)                          ,
                                                      run_id         = Safe_Str__Pipeline__Run__Id(run_id or '')     ,
                                                      region         = Safe_Str__AWS__Region(region or '')           ,
                                                      dry_run        = bool(dry_run)                                 )

        loader      = build_events_loader()
        import time as _time
        t0          = _time.time()
        response    = loader.load(request=request, base_url=base_url, username='elastic', password=elastic_pwd)
        wall_ms     = int((_time.time() - t0) * 1000)

        # ─── render summary ─────────────────────────────────────────────────
        c.print()
        title_suffix = '  [yellow](dry-run)[/]' if response.dry_run else ''
        c.print(f'  [bold]CloudFront events load[/]{title_suffix}')
        c.print()
        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column(style='dim', justify='right')
        t.add_column(style='bold')
        t.add_row('stack'             , str(response.stack_name      ))
        t.add_row('run-id'            , str(response.run_id          ))
        t.add_row('queue-mode'        , str(response.queue_mode      ))
        t.add_row('bucket'            , str(response.bucket          ))
        t.add_row('prefix'            , str(response.prefix_resolved ) or '[dim](full bucket)[/]')
        t.add_row('files-queued'      , str(response.files_queued    ))
        t.add_row('files-processed'   , str(response.files_processed ))
        if response.files_skipped > 0:
            t.add_row('files-skipped' , f'[yellow]{response.files_skipped}[/]')
        if not response.dry_run:
            t.add_row('events-indexed', str(response.events_indexed  ))
            t.add_row('events-updated', str(response.events_updated  ))
            t.add_row('inventory-flips', str(response.inventory_updated))
        t.add_row('bytes-total'       , f'{response.bytes_total:,}')
        t.add_row('wall-time'         , f'{wall_ms} ms')
        if not response.dry_run:
            t.add_row('http-status'   , str(response.last_http_status))
            t.add_row('kibana-url'    , str(response.kibana_url      ))
        c.print(t)

        if str(response.error_message):                                              # Surface failures the same way slice 1 does
            c.print()
            c.print(f'  [yellow]⚠[/]  {rich_escape(str(response.error_message))}')
            if response.last_http_status == 401 or response.last_http_status == 403:
                c.print('     [dim]› Likely SG_ELASTIC_PASSWORD does not match the live stack.[/]')

        if not response.dry_run and response.events_indexed + response.events_updated > 0:
            c.print()
            c.print(f'  [green]✓[/]  Open Kibana Discover at [bold]{base_url}/app/discover[/]')

        c.print()

    _run()


# ───────────────────────────────────────────────────────────────────────────────
# `sp el lets cf events wipe` — matched pair to events load
# ───────────────────────────────────────────────────────────────────────────────

@events_app.command('wipe')
def cmd_events_wipe(stack_name : Optional[str] = typer.Argument(None,                  help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
                     password   : Optional[str] = typer.Option  (None, '--password',    help='Elastic password (else $SG_ELASTIC_PASSWORD).'),
                     region     : Optional[str] = typer.Option  (None, '--region',      help='AWS region (defaults to current AWS_Config session region).'),
                     yes        : bool          = typer.Option  (False, '--yes', '-y',  help='Skip the y/N confirmation prompt.')):
    """Drop every sg-cf-events-* index, the data view, the dashboard, AND reset the inventory manifest's content_processed flags. Idempotent: a second wipe returns all-zeros."""
    from scripts.elastic                                                             import build_service, resolve_stack_name, aws_error_handler, rich_escape

    @aws_error_handler
    def _run():
        c = Console(highlight=False)

        if not password and not os.environ.get('SG_ELASTIC_PASSWORD'):
            c.print('\n  [yellow]⚠[/]  SG_ELASTIC_PASSWORD is not set.\n')
            raise typer.Exit(1)

        service       = build_service()
        stack_picked  = resolve_stack_name(service, stack_name, region)
        info          = service.get_stack_info(stack_name = Safe_Str__Elastic__Stack__Name(stack_picked),
                                                region     = region or '')
        if not str(info.kibana_url):
            c.print(f'\n  [red]✗  Stack [bold]{stack_picked}[/] has no Kibana URL yet.[/]\n')
            raise typer.Exit(1)

        if not yes:
            c.print(f'\n  [yellow]About to wipe all CloudFront-events data on [bold]{stack_picked}[/]:[/]')
            c.print('    [dim]·[/] every [bold]sg-cf-events-*[/] index')
            c.print('    [dim]·[/] the [bold]sg-cf-events-*[/] data view')
            c.print('    [dim]·[/] the [bold]CloudFront Logs - Events Overview[/] dashboard + visualisations')
            c.print('    [dim]·[/] reset every inventory doc\'s [bold]content_processed=true[/] back to false')
            if not typer.confirm('\n  Proceed?', default=False):
                c.print('  [dim]aborted[/]\n')
                raise typer.Exit(0)

        base_url    = str(info.kibana_url).rstrip('/')
        elastic_pwd = password or os.environ.get('SG_ELASTIC_PASSWORD', '')
        wiper       = build_events_wiper()
        response    = wiper.wipe(base_url   = base_url                                            ,
                                  username   = 'elastic'                                           ,
                                  password   = elastic_pwd                                         ,
                                  stack_name = Safe_Str__Elastic__Stack__Name(stack_picked)        )

        c.print()
        total_dropped = (response.indices_dropped + response.data_views_dropped
                          + response.saved_objects_dropped + response.inventory_reset_count)
        if total_dropped == 0:
            c.print(f'  [green]✓[/]  Already clean — nothing to wipe on [bold]{stack_picked}[/]')
        else:
            c.print(f'  [green]✓[/]  Wiped CloudFront events on [bold]{stack_picked}[/]')
        c.print()
        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column(style='dim', justify='right')
        t.add_column(style='bold')
        t.add_row('indices-dropped'      , str(response.indices_dropped      ))
        t.add_row('data-views-dropped'   , str(response.data_views_dropped   ))
        t.add_row('saved-objects-dropped', str(response.saved_objects_dropped))
        t.add_row('inventory-resets'     , str(response.inventory_reset_count))
        t.add_row('duration'             , f'{response.duration_ms} ms')
        c.print(t)

        if str(response.error_message):
            c.print()
            c.print(f'  [yellow]⚠[/]  {rich_escape(str(response.error_message))}')
        c.print()

    _run()
