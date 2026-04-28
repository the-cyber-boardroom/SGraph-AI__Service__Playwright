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
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Events__Read                 import Events__Read
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Events__Wiper                import Events__Wiper
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Reader  import Inventory__Manifest__Reader
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Inventory__Manifest__Updater import Inventory__Manifest__Updater
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.Progress__Reporter            import Progress__Reporter
from sgraph_ai_service_playwright__cli.elastic.lets.cf.events.service.S3__Object__Fetcher          import S3__Object__Fetcher

# sg-send convenience verbs:
from sgraph_ai_service_playwright__cli.elastic.lets.cf.sg_send.service.SG_Send__Date__Parser      import parse_sg_send_date, render_date_label, s3_prefix_for_date
from sgraph_ai_service_playwright__cli.elastic.lets.cf.sg_send.service.SG_Send__File__Viewer      import SG_Send__File__Viewer
from sgraph_ai_service_playwright__cli.elastic.lets.cf.sg_send.service.SG_Send__Inventory__Query  import SG_Send__Inventory__Query
from sgraph_ai_service_playwright__cli.elastic.lets.cf.sg_send.service.SG_Send__Orchestrator      import SG_Send__Orchestrator
from sgraph_ai_service_playwright__cli.elastic.lets.cf.sg_send.schemas.Schema__SG_Send__Sync__Request import Schema__SG_Send__Sync__Request

# Phase B journal — recorded by every loader run:
from sgraph_ai_service_playwright__cli.elastic.lets.runs.service.Pipeline__Runs__Tracker          import Pipeline__Runs__Tracker


# ───────────────────────────────────────────────────────────────────────────────
# Console-rendered progress reporter for `events load`
# Lives in the CLI module because it depends on Rich Console.
# ───────────────────────────────────────────────────────────────────────────────

class Console__Progress__Reporter(Progress__Reporter):                              # Type_Safe subclass — just hooks the no-op base methods to Console output
    console : Console                                                               # Provided by the CLI command

    def on_queue_built(self, files_queued: int, queue_mode: str):
        if files_queued == 0:
            self.console.print(f'\n  [yellow]Queue is empty[/]  [dim](mode: {queue_mode})[/]\n')
            return
        self.console.print(f'\n  [bold]Processing {files_queued} files[/]  [dim](mode: {queue_mode})[/]')

    def on_skip_filter_done(self, before: int, after: int):
        skipped = before - after
        if skipped > 0:
            self.console.print(f'  [dim]--skip-processed:[/] [green]{skipped}[/] already-processed file(s) skipped, [bold]{after}[/] to fetch')

    def on_file_done(self, idx: int, total: int, key: str, events_count: int, duration_ms: int, timings=None):
        # Truncate to last path segment for readability (the .gz filename)
        short_key = key.rsplit('/', 1)[-1] if len(key) > 60 else key
        breakdown = ''
        if timings is not None and timings.total() > 0:
            breakdown = f'  [dim]({timings.render_compact()})[/]'
        self.console.print(f'  [dim][{idx:>3}/{total}][/]  {short_key:<70} [bold]{events_count:>4}[/] events  [dim]{duration_ms:>5} ms[/]{breakdown}')

    def on_file_error(self, idx: int, total: int, key: str, error_msg: str):
        short_key = key.rsplit('/', 1)[-1] if len(key) > 60 else key
        # Inline-escape bracket chars to avoid breaking Rich markup (rich_escape is lazily-imported inside each cmd to dodge a circular import; can't use it from this module-level class)
        safe_msg = (error_msg or '').replace('[', r'\[').replace(']', r'\]')[:200]
        self.console.print(f'  [red][{idx:>3}/{total}][/]  {short_key:<70} [red]error:[/] {safe_msg}')

    def on_load_complete(self):
        self.console.print()


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
sg_send_app   = typer.Typer(help = 'SGraph-Send convenience verbs over the CloudFront LETS pipelines (date-driven, hardcoded sgraph-send specifics).',
                            no_args_is_help = True)

app.add_typer(cf_app, name='cf')
cf_app.add_typer(inventory_app, name='inventory')
cf_app.add_typer(events_app   , name='events')
cf_app.add_typer(sg_send_app  , name='sg-send')


def build_inventory_loader() -> Inventory__Loader:                                  # Single construction site so tests and CLI share the wiring
    http_client = Inventory__HTTP__Client()
    return Inventory__Loader(s3_lister     = S3__Inventory__Lister()                       ,
                              http_client   = http_client                                    ,
                              kibana_client = Kibana__Saved_Objects__Client()                ,
                              run_id_gen    = Run__Id__Generator()                           ,
                              runs_tracker  = Pipeline__Runs__Tracker(http_client=http_client))   # Reuse the same client so the journal write counts as one elastic_call on the same counter


def build_inventory_wiper() -> Inventory__Wiper:
    return Inventory__Wiper(http_client   = Inventory__HTTP__Client()       ,
                             kibana_client = Kibana__Saved_Objects__Client() )


def build_inventory_read() -> Inventory__Read:
    return Inventory__Read(http_client   = Inventory__HTTP__Client()       ,
                            kibana_client = Kibana__Saved_Objects__Client() )


def build_events_loader(progress_reporter: Optional[Progress__Reporter] = None) -> Events__Loader:  # Composition root for the events pipeline.  Reporter optional — defaults to no-op base.
    http_client = Inventory__HTTP__Client()                                          # Single client reused by the loader and the runs tracker — journal write reuses the same counter
    kwargs = dict(s3_lister        = S3__Inventory__Lister()                                    ,
                   s3_fetcher       = S3__Object__Fetcher()                                      ,
                   parser           = CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier()),
                   http_client      = http_client                                                ,
                   kibana_client    = Kibana__Saved_Objects__Client()                            ,
                   manifest_reader  = Inventory__Manifest__Reader (http_client=Inventory__HTTP__Client()),
                   manifest_updater = Inventory__Manifest__Updater(http_client=Inventory__HTTP__Client()),
                   run_id_gen       = Run__Id__Generator()                                        ,
                   runs_tracker     = Pipeline__Runs__Tracker(http_client=http_client)            )
    if progress_reporter is not None:
        kwargs['progress_reporter'] = progress_reporter
    return Events__Loader(**kwargs)


def build_events_wiper() -> Events__Wiper:
    return Events__Wiper(http_client      = Inventory__HTTP__Client()                                    ,
                          kibana_client    = Kibana__Saved_Objects__Client()                              ,
                          manifest_updater = Inventory__Manifest__Updater(http_client=Inventory__HTTP__Client()))


def build_events_read() -> Events__Read:
    return Events__Read(http_client   = Inventory__HTTP__Client()       ,
                         kibana_client = Kibana__Saved_Objects__Client() )


def build_sg_send_inventory_query() -> SG_Send__Inventory__Query:
    return SG_Send__Inventory__Query(http_client = Inventory__HTTP__Client())


def build_sg_send_file_viewer() -> SG_Send__File__Viewer:
    return SG_Send__File__Viewer(s3_fetcher = S3__Object__Fetcher()                                       ,
                                  parser     = CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier()) )


def build_sg_send_orchestrator(progress_reporter: Optional[Progress__Reporter] = None) -> SG_Send__Orchestrator:
    # One shared Call__Counter injected into every collaborator so tallies span both pipeline phases.
    from sgraph_ai_service_playwright__cli.elastic.lets.Call__Counter import Call__Counter
    shared_counter  = Call__Counter()
    inv_http        = Inventory__HTTP__Client(counter=shared_counter)
    inv_lister      = S3__Inventory__Lister  (counter=shared_counter)
    inv_loader      = Inventory__Loader(s3_lister     = inv_lister                      ,
                                         http_client   = inv_http                        ,
                                         kibana_client = Kibana__Saved_Objects__Client() ,
                                         run_id_gen    = Run__Id__Generator()            )
    ev_kwargs = dict(s3_lister        = S3__Inventory__Lister  (counter=shared_counter)                                        ,
                      s3_fetcher       = S3__Object__Fetcher    (counter=shared_counter)                                        ,
                      parser           = CF__Realtime__Log__Parser(bot_classifier=Bot__Classifier())                            ,
                      http_client      = Inventory__HTTP__Client (counter=shared_counter)                                       ,
                      kibana_client    = Kibana__Saved_Objects__Client()                                                        ,
                      manifest_reader  = Inventory__Manifest__Reader (http_client=Inventory__HTTP__Client(counter=shared_counter)),
                      manifest_updater = Inventory__Manifest__Updater(http_client=Inventory__HTTP__Client(counter=shared_counter)),
                      run_id_gen       = Run__Id__Generator()                                                                   )
    if progress_reporter is not None:
        ev_kwargs['progress_reporter'] = progress_reporter
    ev_loader = Events__Loader(**ev_kwargs)
    return SG_Send__Orchestrator(counter          = shared_counter ,
                                  inventory_loader = inv_loader     ,
                                  events_loader    = ev_loader      )


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
                    skip_processed  : bool          = typer.Option  (False, '--skip-processed',  help='Query the inventory manifest (sg-cf-inventory-*) for etags with content_processed=true FIRST and filter them out of the queue. Single source of truth — covers 0-event files (which never appear in sg-cf-events-*). Cheap (one ES aggregation).'),
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
                                                      skip_processed = bool(skip_processed)                          ,
                                                      run_id         = Safe_Str__Pipeline__Run__Id(run_id or '')     ,
                                                      region         = Safe_Str__AWS__Region(region or '')           ,
                                                      dry_run        = bool(dry_run)                                 )

        # Build the loader with a Console-rendered progress reporter so the
        # per-file loop isn't silent.  Reporter is a no-op for dry_run
        # (build_queue runs but the per-file loop doesn't).
        reporter    = Console__Progress__Reporter(console=c)
        loader      = build_events_loader(progress_reporter=reporter)
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


# ───────────────────────────────────────────────────────────────────────────────
# `sp el lets cf events list` — show distinct events runs
# ───────────────────────────────────────────────────────────────────────────────

@events_app.command('list')
def cmd_events_list(stack_name : Optional[str] = typer.Argument(None,                  help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
                     password   : Optional[str] = typer.Option  (None, '--password',    help='Elastic password (else $SG_ELASTIC_PASSWORD).'),
                     region     : Optional[str] = typer.Option  (None, '--region',      help='AWS region (defaults to current AWS_Config session region).'),
                     top_n      : int           = typer.Option  (100,  '--top',         help='Show at most N runs (default 100).')):
    """List distinct pipeline runs currently indexed in sg-cf-events-*. One row per pipeline_run_id."""
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
        reader      = build_events_read()
        runs        = reader.list_runs(base_url=base_url, username='elastic', password=elastic_pwd, top_n=top_n)

        c.print()
        if len(runs) == 0:
            c.print(f'  [dim]No runs in sg-cf-events-* on [bold]{stack_picked}[/].  Run `sp el lets cf events load`.[/]\n')
            return

        c.print(f'  [bold]Events runs on [cyan]{stack_picked}[/cyan][/]')
        c.print()
        t = Table(show_header=True, header_style='bold', box=None, padding=(0, 2))
        t.add_column('Run id'  , style='dim')
        t.add_column('Events'  , justify='right')
        t.add_column('Files'   , justify='right')
        t.add_column('Bytes'   , justify='right')
        t.add_column('Event range')
        t.add_column('Loaded at')
        for run in runs:
            event_range = str(run.earliest_event)[:10]
            if str(run.latest_event)[:10] != event_range:
                event_range = f'{event_range} → {str(run.latest_event)[:10]}'
            loaded_at = str(run.latest_loaded).replace('T', ' ').rstrip('Z').split('.')[0]
            t.add_row(str(run.pipeline_run_id),
                       str(run.event_count    ),
                       str(run.file_count     ),
                       f'{int(run.bytes_total):,}',
                       event_range,
                       loaded_at)
        c.print(t)
        c.print(f'\n  [dim]{len(runs)} run(s)[/]\n')

    _run()


# ───────────────────────────────────────────────────────────────────────────────
# `sp el lets cf events health` — check the events-pipeline plumbing
# ───────────────────────────────────────────────────────────────────────────────

@events_app.command('health')
def cmd_events_health(stack_name : Optional[str] = typer.Argument(None,                help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
                       password   : Optional[str] = typer.Option  (None, '--password',  help='Elastic password (else $SG_ELASTIC_PASSWORD).'),
                       region     : Optional[str] = typer.Option  (None, '--region',    help='AWS region (defaults to current AWS_Config session region).')):
    """Check the events dataset's plumbing: indices, data view, dashboard + bonus inventory-link coverage row."""
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
        reader      = build_events_read()
        response    = reader.health(base_url=base_url, username='elastic', password=elastic_pwd,
                                     stack_name=Safe_Str__Elastic__Stack__Name(stack_picked))

        icon_for = {'ok': '[green]✓[/]', 'warn': '[yellow]⚠[/]', 'fail': '[red]✗[/]', 'skip': '[dim]·[/]'}
        has_warn    = any(str(chk.status) == 'warn' for chk in response.checks)
        rollup_icon = '[red]✗[/]' if not response.all_ok else ('[yellow]⚠[/]' if has_warn else '[green]✓[/]')
        c.print()
        c.print(f'  {rollup_icon}  Events health for [bold]{stack_picked}[/]')
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
# `sp el lets cf sg-send sync [DATE]` — daily refresh (inventory + events)
# ───────────────────────────────────────────────────────────────────────────────
# Runs inventory load → events load (from_inventory=True) for one calendar
# date, sharing one Call__Counter across all collaborators so the summary
# reports unified S3/Elastic call counts.

SG_SEND__DEFAULT_BUCKET = '745506449035--sgraph-send-cf-logs--eu-west-2'


@sg_send_app.command('sync')
def cmd_sg_send_sync(date_spec  : Optional[str] = typer.Argument(None,                      help='Date spec: MM/DD or YYYY-MM-DD. Defaults to today UTC.'),
                     stack_name : Optional[str] = typer.Option  (None, '--stack',           help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
                     max_files  : int           = typer.Option  (0,   '--max-files',        help='Cap on events load. 0 = unlimited.'),
                     password   : Optional[str] = typer.Option  (None, '--password',        help='Elastic password (else $SG_ELASTIC_PASSWORD).'),
                     region     : Optional[str] = typer.Option  (None, '--region',          help='AWS region (defaults to current AWS_Config session region).'),
                     dry_run    : bool          = typer.Option  (False, '--dry-run',        help='List + parse only; skip bulk-post and manifest updates.')):
    """Daily refresh: inventory load → events load (from-inventory) for one date. Single shared Call__Counter."""
    from scripts.elastic                                                             import build_service, resolve_stack_name, aws_error_handler, rich_escape
    from datetime                                                                    import datetime, timezone
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.inventory.primitives.Safe_Str__S3__Bucket import Safe_Str__S3__Bucket
    from osbot_utils.type_safe.primitives.domains.common.safe_str.Safe_Str__Text     import Safe_Str__Text

    @aws_error_handler
    def _run():
        c = Console(highlight=False)

        if not dry_run and not password and not os.environ.get('SG_ELASTIC_PASSWORD'):
            c.print('\n  [yellow]⚠[/]  SG_ELASTIC_PASSWORD is not set.')
            c.print('     [dim]Re-export it from the most recent `sp elastic create` output, e.g.:[/]')
            c.print('     [bold]export SG_ELASTIC_PASSWORD=<password-from-create>[/]')
            c.print('     [dim]Or pass it explicitly via --password.[/]\n')
            raise typer.Exit(1)

        # ─── resolve sync date ───────────────────────────────────────────────
        if date_spec:
            try:
                year, month, day, _ = parse_sg_send_date(date_spec)
            except ValueError as exc:
                c.print(f'\n  [red]✗[/]  {rich_escape(str(exc))}\n')
                raise typer.Exit(1)
            sync_date_iso = f'{year:04d}-{month:02d}-{day:02d}'
        else:
            sync_date_iso = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        service       = build_service()
        stack_picked  = resolve_stack_name(service, stack_name, region)
        info          = service.get_stack_info(stack_name = Safe_Str__Elastic__Stack__Name(stack_picked),
                                                region     = region or '')
        if not str(info.kibana_url):
            c.print(f'\n  [red]✗  Stack [bold]{stack_picked}[/] has no Kibana URL yet.[/]  Run `sp el wait` first.\n')
            raise typer.Exit(1)

        base_url    = str(info.kibana_url).rstrip('/')
        elastic_pwd = password or os.environ.get('SG_ELASTIC_PASSWORD', '')

        request = Schema__SG_Send__Sync__Request(sync_date  = Safe_Str__Text(sync_date_iso)                       ,
                                                  max_files  = int(max_files)                                      ,
                                                  dry_run    = bool(dry_run)                                       ,
                                                  bucket     = Safe_Str__S3__Bucket(SG_SEND__DEFAULT_BUCKET)       ,
                                                  region     = Safe_Str__AWS__Region(region or '')                 ,
                                                  stack_name = Safe_Str__Elastic__Stack__Name(stack_picked)        )

        reporter  = Console__Progress__Reporter(console=c)
        orch      = build_sg_send_orchestrator(progress_reporter=reporter)

        c.print()
        title_suffix = '  [yellow](dry-run)[/]' if dry_run else ''
        c.print(f'  [bold]SGraph-Send sync[/]{title_suffix}  [cyan]{sync_date_iso}[/]')
        c.print(f'  [dim]stack:[/] {stack_picked}   [dim]max-files:[/] {max_files or "unlimited"}')
        c.print()

        response  = orch.sync(request  = request    ,
                               base_url = base_url   ,
                               username = 'elastic'  ,
                               password = elastic_pwd)

        # ─── render inventory summary ────────────────────────────────────────
        ir = response.inventory_response
        c.print(f'  [bold]inventory[/]  phase')
        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column(style='dim', justify='right')
        t.add_column(style='bold')
        t.add_row('prefix'          , str(ir.prefix_resolved) or '[dim](full bucket)[/]')
        t.add_row('pages-listed'    , str(ir.pages_listed    ))
        t.add_row('objects-scanned' , str(ir.objects_scanned ))
        if not dry_run:
            t.add_row('objects-indexed', str(ir.objects_indexed))
            t.add_row('objects-updated', str(ir.objects_updated))
        t.add_row('bytes-total'     , f'{ir.bytes_total:,}')
        if not dry_run:
            t.add_row('http-status' , str(ir.last_http_status))
        c.print(t)
        if str(ir.error_message):
            c.print(f'  [red]✗[/]  inventory error: {rich_escape(str(ir.error_message))}')

        c.print()

        # ─── render events summary ───────────────────────────────────────────
        er = response.events_response
        c.print(f'  [bold]events[/]  phase  [dim](from-inventory)[/]')
        t2 = Table(show_header=False, box=None, padding=(0, 2))
        t2.add_column(style='dim', justify='right')
        t2.add_column(style='bold')
        t2.add_row('files-queued'   , str(er.files_queued   ))
        t2.add_row('files-processed', str(er.files_processed))
        t2.add_row('files-skipped'  , str(er.files_skipped  ))
        if not dry_run:
            t2.add_row('events-indexed', str(er.events_indexed ))
        t2.add_row('bytes-total'    , f'{er.bytes_total:,}')
        if not dry_run:
            t2.add_row('http-status', str(er.last_http_status))
        c.print(t2)
        if str(er.error_message):
            c.print(f'  [red]✗[/]  events error: {rich_escape(str(er.error_message))}')

        c.print()

        # ─── render totals ───────────────────────────────────────────────────
        t3 = Table(show_header=False, box=None, padding=(0, 2))
        t3.add_column(style='dim', justify='right')
        t3.add_column(style='bold')
        t3.add_row('s3-calls-total'      , str(response.s3_calls_total     ))
        t3.add_row('elastic-calls-total' , str(response.elastic_calls_total ))
        t3.add_row('wall-time'           , f'{response.wall_ms} ms'          )
        if not dry_run:
            t3.add_row('kibana-url'      , str(ir.kibana_url                ))
        c.print(t3)
        c.print()

    _run()


# ───────────────────────────────────────────────────────────────────────────────
# `sp el lets cf sg-send files <date>` — list inventory rows for a day or hour
# ───────────────────────────────────────────────────────────────────────────────
# Reads sg-cf-inventory-* (no S3 calls).  One ES query.  Renders a compact
# table: time, key (filename only), size, processed flag, etag prefix.
# Useful for spotting "lots of files but no events" before fetching anything.


@sg_send_app.command('files')
def cmd_sg_send_files(date_spec  : str            = typer.Argument(...,                       help='Date spec: MM/DD, MM/DD/HH, YYYY/MM/DD, or YYYY/MM/DD/HH. Year defaults to 2026.'),
                      stack_name : Optional[str]  = typer.Option  (None, '--stack',           help='Stack name. Auto-picks when only one stack exists; prompts on multiple.'),
                      password   : Optional[str]  = typer.Option  (None, '--password',        help='Elastic password (else $SG_ELASTIC_PASSWORD).'),
                      region     : Optional[str]  = typer.Option  (None, '--region',          help='AWS region (defaults to current AWS_Config session region).'),
                      page_size  : int            = typer.Option  (1000, '--page-size',       help='Max rows to return from Elastic (default 1000).')):
    """List inventory rows for a date or hour. Reads sg-cf-inventory-* only — no S3 calls."""
    from scripts.elastic                                                             import build_service, resolve_stack_name, aws_error_handler, rich_escape

    @aws_error_handler
    def _run():
        c = Console(highlight=False)

        try:
            year, month, day, hour = parse_sg_send_date(date_spec)
        except ValueError as exc:
            c.print(f'\n  [red]✗[/]  {rich_escape(str(exc))}\n')
            raise typer.Exit(1)

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
        query       = build_sg_send_inventory_query()
        import time as _time
        t0          = _time.time()
        rows, status, err = query.list_files_for_date(base_url=base_url, username='elastic', password=elastic_pwd,
                                                        year=year, month=month, day=day, hour=hour,
                                                        page_size=page_size)
        wall_ms     = int((_time.time() - t0) * 1000)

        c.print()
        c.print(f'  [bold]CloudFront inventory files[/] · [cyan]{render_date_label(year, month, day, hour)}[/]')
        c.print(f'  [dim]stack:[/] {stack_picked}   [dim]http:[/] {status}   [dim]wall:[/] {wall_ms} ms   [dim]rows:[/] {len(rows)}')
        c.print()

        if err:
            c.print(f'  [yellow]⚠[/]  {rich_escape(err)}\n')
            return

        if len(rows) == 0:
            c.print(f'  [dim]No inventory rows for {render_date_label(year, month, day, hour)}.  Run `sp el lets cf inventory load --prefix cloudfront-realtime/{year:04d}/{month:02d}/{day:02d}/`[/]\n')
            return

        # ─── render rows ────────────────────────────────────────────────────
        t = Table(show_header=True, header_style='bold', box=None, padding=(0, 2))
        t.add_column('Time',    style='dim'   )
        t.add_column('Key',                    )
        t.add_column('Size',    justify='right')
        t.add_column('Done',    justify='center')
        t.add_column('Etag',    style='dim'   )
        total_bytes  = 0
        processed_n  = 0
        for row in rows:
            full_key   = str(row.get('key', ''))
            short_key  = full_key.rsplit('/', 1)[-1] or full_key
            delivery   = str(row.get('delivery_at', ''))
            time_part  = delivery[11:19] if len(delivery) >= 19 else delivery        # "HH:MM:SS" extracted from ISO timestamp
            size       = int(row.get('size_bytes', 0))
            processed  = bool(row.get('content_processed', False))
            etag       = str(row.get('etag', ''))[:8]
            total_bytes += size
            if processed:
                processed_n += 1
            t.add_row(time_part,
                       short_key,
                       f'{size:,}',
                       '[green]✓[/]' if processed else '[dim]–[/]',
                       etag)
        c.print(t)
        c.print()
        c.print(f'  [dim]totals:[/] [bold]{len(rows)}[/] file(s), [bold]{total_bytes:,}[/] bytes, [bold]{processed_n}[/]/{len(rows)} processed')
        c.print()

    _run()


# ───────────────────────────────────────────────────────────────────────────────
# `sp el lets cf sg-send view <key>` — fetch a single .gz, show raw or table
# ───────────────────────────────────────────────────────────────────────────────
# One S3 GetObject + gunzip.  Default: print the raw TSV (so you can pipe it
# to `head` / `wc -l`).  --table: render parsed events in a Rich table for
# eyeballing.  Useful for confirming a 0-event file really is empty/garbage.

@sg_send_app.command('view')
def cmd_sg_send_view(key        : str            = typer.Argument(...,                       help='Full S3 key (e.g. cloudfront-realtime/2026/04/25/14/EXXXX.2026-04-25-14.abcd1234.gz). Use `sg-send files <date>` to list keys.'),
                     bucket     : Optional[str]  = typer.Option  (None, '--bucket',          help='S3 bucket (defaults to the SGraph CloudFront-logs bucket).'),
                     region     : Optional[str]  = typer.Option  (None, '--region',          help='AWS region (defaults to current AWS_Config session region).'),
                     table      : bool           = typer.Option  (False, '--table',          help='Parse the TSV and render a Rich table of events instead of dumping the raw text.'),
                     limit      : int            = typer.Option  (50,   '--limit',           help='With --table, render at most N events (default 50). 0 = unlimited.')):
    """Fetch a single CloudFront .gz and dump it. Default: raw TSV. --table: parsed events."""
    from scripts.elastic                                                             import aws_error_handler, rich_escape

    @aws_error_handler
    def _run():
        c = Console(highlight=False)

        bucket_resolved = bucket or SG_SEND__DEFAULT_BUCKET
        viewer          = build_sg_send_file_viewer()
        import time as _time
        t0              = _time.time()

        if table:
            try:
                records, skipped = viewer.parsed(bucket=bucket_resolved, key=key, region=region or '')
            except Exception as exc:
                c.print(f'\n  [red]✗[/]  fetch/parse error: {rich_escape(str(exc)[:300])}\n')
                raise typer.Exit(1)
            wall_ms = int((_time.time() - t0) * 1000)

            c.print()
            c.print(f'  [bold]{key}[/]')
            c.print(f'  [dim]bucket:[/] {bucket_resolved}   [dim]events:[/] {len(records)}   [dim]skipped lines:[/] {skipped}   [dim]wall:[/] {wall_ms} ms')
            c.print()

            if len(records) == 0:
                c.print('  [dim](no parseable events in this file)[/]\n')
                return

            shown = records if limit == 0 else records[:limit]
            tbl = Table(show_header=True, header_style='bold', box=None, padding=(0, 1))
            tbl.add_column('Time',    style='dim')
            tbl.add_column('Status',  justify='right')
            tbl.add_column('Method',                  )
            tbl.add_column('Host',                    )
            tbl.add_column('URI',                     )
            tbl.add_column('Country', justify='center')
            tbl.add_column('Bot',                     )
            tbl.add_column('UA',      style='dim'    )
            for r in shown:
                ts        = str(r.timestamp)
                time_part = ts[11:19] if len(ts) >= 19 else ts
                ua_short  = str(r.cs_user_agent)[:60]
                tbl.add_row(time_part,
                             str(int(r.sc_status)),
                             str(r.cs_method.value if hasattr(r.cs_method, 'value') else r.cs_method),
                             str(r.cs_host)[:30],
                             str(r.cs_uri_stem)[:40],
                             str(r.c_country) or '-',
                             str(r.bot_category.value if hasattr(r.bot_category, 'value') else r.bot_category),
                             ua_short)
            c.print(tbl)
            if limit > 0 and len(records) > limit:
                c.print(f'\n  [dim]…showing {limit} of {len(records)} events.  Pass --limit 0 for all.[/]')
            c.print()
        else:
            try:
                tsv_text = viewer.raw_text(bucket=bucket_resolved, key=key, region=region or '')
            except Exception as exc:
                c.print(f'\n  [red]✗[/]  fetch error: {rich_escape(str(exc)[:300])}\n')
                raise typer.Exit(1)
            wall_ms = int((_time.time() - t0) * 1000)

            c.print()
            c.print(f'  [bold]{key}[/]  [dim]({len(tsv_text):,} bytes, {wall_ms} ms)[/]')
            c.print()
            # Use plain print, not rich, so the TSV pipes cleanly to head/wc/grep
            print(tsv_text, end='' if tsv_text.endswith('\n') else '\n')

    _run()
