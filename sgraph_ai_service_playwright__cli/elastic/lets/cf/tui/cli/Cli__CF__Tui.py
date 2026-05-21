# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: Cli__CF__Tui
# `... tui <screen>` — the exploratory CloudFront-logs TUI screens. Textual is
# imported lazily inside each command so merely registering this sub-app never
# requires textual — the rest of the CLI works whether or not textual is present.
#
#   traffic    Screen 5 — Traffic Reality (what is going on on the website)
#   files      S3 browser — walk folders (YYYY/MM/DD/HH) → file → its parsed contents
#   inspect    Field Lineage — one log line walked through all 38 fields raw→transformed
#   diagnose   deployment-chain self-check (TERM / LANG / unicode / truecolor)
#
# --source in-memory|s3 picks the data source (default in-memory fixtures → runs with
# no AWS). --date/--hour/--max-files scope the S3 reads. When stdout is not a TTY the
# screen falls back to a static text view and exits — safe to pipe.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys

import typer

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__config   import CF_LOGS_BUCKET, CF_LOGS_PREFIX, CF_LOGS_REGION, TUI_S3_SAMPLE_FILES

app = typer.Typer(name='tui', help='CloudFront-logs exploratory TUI screens (Textual).', no_args_is_help=True)

_source_factory = None                                                               # tests assign a callable(source, bucket, prefix, region, date, hour, max_files) → Data_Source
_arch_factory   = None                                                               # tests assign a callable(bucket, region) → CF_TUI__Arch_Source
_sync_factory   = None                                                               # tests assign a callable(bucket, region) → CF__Logs__Sync
_store_factory  = None                                                               # tests assign a callable() → CF__Local__Store


@app.callback()
def main():                                                                          # force group behaviour — keeps `tui <screen>` valid
    pass


def _source(source : str, bucket : str, prefix : str, region : str, date : str, hour : str, max_files : int):
    if _source_factory is not None:
        return _source_factory(source, bucket, prefix, region, date, hour, max_files)
    if str(source) == 's3':
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.source.CF_TUI__S3_Source import CF_TUI__S3_Source
        return CF_TUI__S3_Source(bucket       = bucket or CF_LOGS_BUCKET,
                                 prefix       = prefix or CF_LOGS_PREFIX,
                                 region       = region or CF_LOGS_REGION,
                                 date_iso     = date,
                                 hour         = hour,
                                 sample_files = max_files or TUI_S3_SAMPLE_FILES).setup()
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.source.CF_TUI__In_Memory_Source import CF_TUI__In_Memory_Source
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__fixtures             import fixture_files
    return CF_TUI__In_Memory_Source(files=fixture_files()).setup()


def _start_prefix(source : str, data_source) -> str:                                 # where the folder browser opens
    if str(source) == 's3':
        return data_source.scoped_prefix()
    return ''


# ─── shared options ──────────────────────────────────────────────────────────
SOURCE = typer.Option('in-memory', '--source', '-s', help='Data source: in-memory | s3')
BUCKET = typer.Option('',          '--bucket',        help='S3 bucket (s3 source; defaults to the CF-logs bucket)')
PREFIX = typer.Option('',          '--prefix',        help='S3 base prefix (s3 source; defaults to cloudfront-realtime/)')
REGION = typer.Option('',          '--region',        help='AWS region (s3 source)')
DATE   = typer.Option('',          '--date',          help='Scope to a day: YYYY-MM-DD (s3 source)')
HOUR   = typer.Option('',          '--hour',          help='Scope to an hour: HH (s3 source; needs --date)')
MAXF   = typer.Option(0,           '--max-files',     help='Max newest objects to load (s3 source)')
KEY    = typer.Option('',          '--key',           help='Object key to inspect (inspect; default: first file)')
LINE   = typer.Option(0,           '--line',          help='Line index within the file (inspect)')


@app.command(name='traffic', help='Screen 5 — Traffic Reality: what is going on on the website.')
def traffic(source : str = SOURCE, bucket : str = BUCKET, prefix : str = PREFIX, region : str = REGION,
            date : str = DATE, hour : str = HOUR, max_files : int = MAXF):
    data_source = _source(source, bucket, prefix, region, date, hour, max_files)
    if not sys.stdout.isatty():
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__Card import CF_TUI__Card
        print(CF_TUI__Card().render(data_source.traffic_snapshot()))
        return
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Screen__Traffic import CF_TUI__Screen__Traffic
    CF_TUI__Screen__Traffic(source=data_source).run()


@app.command(name='files', help='S3 browser — walk folders (YYYY/MM/DD/HH) to a file and its parsed contents.')
def files(source : str = SOURCE, bucket : str = BUCKET, prefix : str = PREFIX, region : str = REGION,
          date : str = DATE, hour : str = HOUR, max_files : int = MAXF):
    data_source = _source(source, bucket, prefix, region, date, hour, max_files)
    start       = _start_prefix(source, data_source)
    if not sys.stdout.isatty():
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Files__Render import dir_browse_plain
        print(dir_browse_plain(list(data_source.list_dir(start)), start))
        return
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Screen__Files import CF_TUI__Screen__Files
    CF_TUI__Screen__Files(source=data_source, start_prefix=start).run()


@app.command(name='inspect', help='Field Lineage — one log line walked through all 38 fields, raw→transformed.')
def inspect(source : str = SOURCE, bucket : str = BUCKET, prefix : str = PREFIX, region : str = REGION,
            date : str = DATE, hour : str = HOUR, max_files : int = MAXF, key : str = KEY, line : int = LINE):
    data_source = _source(source, bucket, prefix, region, date, hour, max_files)
    target_key  = key
    if not target_key:                                                               # default to the first file in the scope
        rows = list(data_source.list_files(date, hour, max_files))
        if rows:
            target_key = rows[0].key
    if not sys.stdout.isatty():
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Inspector__Render import inspector_plain
        print(inspector_plain(data_source.read_record(target_key, line)))
        return
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Screen__Inspector import CF_TUI__Screen__Inspector
    CF_TUI__Screen__Inspector(source=data_source, key=target_key, line_index=line).run()


def _arch_source(bucket : str, region : str):
    if _arch_factory is not None:
        return _arch_factory(bucket, region)
    from sgraph_ai_service_playwright__cli.aws.cf.service.CloudFront__AWS__Client     import CloudFront__AWS__Client
    from sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client         import Logs__AWS__Client
    from sgraph_ai_service_playwright__cli.aws.s3.service.S3__AWS__Client             import S3__AWS__Client
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.source.CF_TUI__Arch_Source import CF_TUI__Arch_Source
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__config         import CF_LOGS_BUCKET
    return CF_TUI__Arch_Source(cf_client   = CloudFront__AWS__Client(),
                               logs_client = Logs__AWS__Client(),
                               s3_client   = S3__AWS__Client(region=region),
                               bucket      = bucket or CF_LOGS_BUCKET)


@app.command(name='architecture', help='Deployed Architecture — live CF/S3/CloudWatch wiring (Firehose marked UNVERIFIED).')
def architecture(bucket : str = BUCKET, region : str = REGION):
    src = _arch_source(bucket, region)
    if not sys.stdout.isatty():
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Arch__Render import arch_plain
        print(arch_plain(src.snapshot()))
        return
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Screen__Arch import CF_TUI__Screen__Arch
    CF_TUI__Screen__Arch(source=src).run()


def _sync_service(bucket : str, region : str):
    if _sync_factory is not None:
        return _sync_factory(bucket, region)
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.service.CF__Logs__Sync   import CF__Logs__Sync
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.service.CF__Local__Store import CF__Local__Store
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__config             import CF_LOGS_BUCKET, CF_LOGS_REGION
    return CF__Logs__Sync(bucket = bucket or CF_LOGS_BUCKET,
                          region = region or CF_LOGS_REGION,
                          store  = CF__Local__Store())


MODE = typer.Option('list', '--mode', '-m', help='list (diff only) | download (fetch missing)')


@app.command(name='sync', help='Sync raw-cf-logs S3 → _vaults. Immutable: only missing objects download. --mode list|download.')
def sync(date : str = DATE, hour : str = HOUR, mode : str = MODE, bucket : str = BUCKET, region : str = REGION):
    svc  = _sync_service(bucket, region)
    if not sys.stdout.isatty():
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Sync__Render import sync_plain
        plan   = svc.plan(date, hour)
        result = svc.download_missing(plan) if str(mode) == 'download' else None
        print(sync_plain(plan, result))
        return
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Screen__Sync import CF_TUI__Screen__Sync
    CF_TUI__Screen__Sync(sync=svc, date_iso=date, hour=hour).run()


@app.command(name='diagnose', help='Deployment-chain self-check: TERM / LANG / unicode / truecolor.')
def diagnose():
    print(f'TERM = {os.environ.get("TERM", "(unset)")}')
    print(f'LANG = {os.environ.get("LANG", "(unset)")}')
    print(f'LC_ALL = {os.environ.get("LC_ALL", "(unset)")}')
    print('unicode  : █▓▒░ ▁▂▃▄▅▆▇█ ╭─╮ │ │ ╰─╯   (boxes/?? → locale or font wrong)')
    print('truecolor: \x1b[38;2;255;100;0mTRUECOLOR\x1b[0m   (orange → 24-bit ok)')
