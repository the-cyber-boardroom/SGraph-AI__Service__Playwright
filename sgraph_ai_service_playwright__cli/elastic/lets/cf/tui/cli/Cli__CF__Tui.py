# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: Cli__CF__Tui
# `... tui <screen>` — the exploratory CloudFront-logs TUI screens. Textual is
# imported lazily inside each command so merely registering this sub-app never
# requires textual — the rest of the CLI works whether or not textual is present.
#
#   traffic    Screen 5 — Traffic Reality (what is going on on the website)
#   files      S3 browser — the .gz files per day + one file's parsed contents
#   diagnose   deployment-chain self-check (TERM / LANG / unicode / truecolor)
#
# --source in-memory|s3 picks the data source (default in-memory fixtures → runs with
# no AWS). --date/--hour/--max-files scope the S3 reads (load more files, walk
# hours/days). When stdout is not a TTY (piped / CI) the screen falls back to a static
# text view and exits — safe to pipe, degrades gracefully over a broken chain.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys

import typer

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__config   import CF_LOGS_BUCKET, CF_LOGS_PREFIX, CF_LOGS_REGION, TUI_S3_SAMPLE_FILES

app = typer.Typer(name='tui', help='CloudFront-logs exploratory TUI screens (Textual).', no_args_is_help=True)

_source_factory = None                                                               # tests assign a callable(source, bucket, prefix, region, date, hour, max_files) → Data_Source


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
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__fixtures             import FIXTURE_TSV
    return CF_TUI__In_Memory_Source(tsv_text=FIXTURE_TSV).setup()


# ─── shared options ──────────────────────────────────────────────────────────
SOURCE = typer.Option('in-memory', '--source', '-s', help='Data source: in-memory | s3')
BUCKET = typer.Option('',          '--bucket',        help='S3 bucket (s3 source; defaults to the CF-logs bucket)')
PREFIX = typer.Option('',          '--prefix',        help='S3 base prefix (s3 source; defaults to cloudfront-realtime/)')
REGION = typer.Option('',          '--region',        help='AWS region (s3 source)')
DATE   = typer.Option('',          '--date',          help='Scope to a day: YYYY-MM-DD (s3 source)')
HOUR   = typer.Option('',          '--hour',          help='Scope to an hour: HH (s3 source; needs --date)')
MAXF   = typer.Option(0,           '--max-files',     help='Max newest objects to load (s3 source)')


@app.command(name='traffic', help='Screen 5 — Traffic Reality: what is going on on the website.')
def traffic(source : str = SOURCE, bucket : str = BUCKET, prefix : str = PREFIX, region : str = REGION,
            date : str = DATE, hour : str = HOUR, max_files : int = MAXF):
    data_source = _source(source, bucket, prefix, region, date, hour, max_files)
    if not sys.stdout.isatty():                                                      # piped / CI / no real terminal → static card
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.service.CF_TUI__Card import CF_TUI__Card
        print(CF_TUI__Card().render(data_source.traffic_snapshot()))
        return
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Screen__Traffic import CF_TUI__Screen__Traffic
    CF_TUI__Screen__Traffic(source=data_source).run()


@app.command(name='files', help='S3 browser — the .gz files per day, and one file\'s parsed contents.')
def files(source : str = SOURCE, bucket : str = BUCKET, prefix : str = PREFIX, region : str = REGION,
          date : str = DATE, hour : str = HOUR, max_files : int = MAXF):
    data_source = _source(source, bucket, prefix, region, date, hour, max_files)
    if not sys.stdout.isatty():                                                      # piped / CI → static listing
        from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Files__Render import files_browse_plain
        scope = data_source.label() + (f'  {date}' + (f' {hour}h' if hour else '') if date else '')
        print(files_browse_plain(data_source.list_files(date, hour, max_files), scope))
        return
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.CF_TUI__Screen__Files import CF_TUI__Screen__Files
    CF_TUI__Screen__Files(source=data_source, date_iso=date, hour=hour, max_files=max_files).run()


@app.command(name='diagnose', help='Deployment-chain self-check: TERM / LANG / unicode / truecolor.')
def diagnose():
    print(f'TERM = {os.environ.get("TERM", "(unset)")}')
    print(f'LANG = {os.environ.get("LANG", "(unset)")}')
    print(f'LC_ALL = {os.environ.get("LC_ALL", "(unset)")}')
    print('unicode  : █▓▒░ ▁▂▃▄▅▆▇█ ╭─╮ │ │ ╰─╯   (boxes/?? → locale or font wrong)')
    print('truecolor: \x1b[38;2;255;100;0mTRUECOLOR\x1b[0m   (orange → 24-bit ok)')
