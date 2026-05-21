# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf local cli: Cli__CF__Local
# The NATIVE, manually-invokable cf-logs cache commands — the canonical path that does
# the work (the TUI is only a visual front-end over these same backend classes):
#   sp el lets cf sync   --date --hour --mode list|download
#   sp el lets cf cache
# Principle (see library/guides/v0.2.39__tui_cli_separation.md): every data retrieval
# or transformation MUST be reachable from the CLI; the TUI never owns logic. The
# service builders + factory seams live here so both the native command and the TUI
# screen construct the work the same way (no duplicated logic).
# ═══════════════════════════════════════════════════════════════════════════════

import typer

from sgraph_ai_service_playwright__cli.aws._shared.auth.AWS__Auth__Guard            import aws_auth_guard
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.cli.CF__Local__Render import sync_plain, cache_plain

FAMILY = 'el-lets-cf'

app = typer.Typer(help='Local raw-cf-logs cache (native CLI; the TUI mirrors these).')

_sync_factory  = None                                                                # tests assign callable(bucket, region) → CF__Logs__Sync
_store_factory = None                                                                # tests assign callable() → CF__Local__Store

DATE   = typer.Option('', '--date',          help='Scope to a day: YYYY-MM-DD')
HOUR   = typer.Option('', '--hour',          help='Scope to an hour: HH (needs --date)')
MODE   = typer.Option('list', '--mode', '-m', help='list (diff only) | download (fetch missing)')
BUCKET = typer.Option('', '--bucket',        help='S3 bucket (defaults to the CF-logs bucket)')
REGION = typer.Option('', '--region',        help='AWS region')


def build_sync_service(bucket : str = '', region : str = ''):
    if _sync_factory is not None:
        return _sync_factory(bucket, region)
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.service.CF__Logs__Sync   import CF__Logs__Sync
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.service.CF__Local__Store import CF__Local__Store
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__config             import CF_LOGS_BUCKET, CF_LOGS_REGION
    return CF__Logs__Sync(bucket = bucket or CF_LOGS_BUCKET,
                          region = region or CF_LOGS_REGION,
                          store  = CF__Local__Store())


def build_local_store():
    if _store_factory is not None:
        return _store_factory()
    from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.service.CF__Local__Store import CF__Local__Store
    return CF__Local__Store()


@app.command('sync', help='Sync raw-cf-logs S3 → _vaults. Immutable: only missing objects download.')
@aws_auth_guard(FAMILY)
def sync(date : str = DATE, hour : str = HOUR, mode : str = MODE, bucket : str = BUCKET, region : str = REGION):
    svc    = build_sync_service(bucket, region)
    plan   = svc.plan(date, hour)
    result = svc.download_missing(plan) if str(mode) == 'download' else None
    print(sync_plain(plan, result))


@app.command('cache', help='Local raw-cf-logs cache stats — files / size / partition coverage.')
@aws_auth_guard(FAMILY)
def cache():
    print(cache_plain(build_local_store().stats()))
