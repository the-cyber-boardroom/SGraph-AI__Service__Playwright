# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf local cli: CF__Local__Render
# Plain-text rendering for the NATIVE cf-logs CLI commands (`sp el lets cf sync` /
# `cache`). This is the CLI layer's presentation — pure, no textual — and the TUI's
# no-TTY fallback also calls it (the TUI depends on the CLI layer, never the reverse).
# The rich-markup variants for the interactive screens live in tui/screens/*.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Local__Stats import Schema__CF__Local__Stats
from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Sync__Plan   import Schema__CF__Sync__Plan
from sgraph_ai_service_playwright__cli.tui.render.Tui__Text                                   import human_size


def _scope(plan : Schema__CF__Sync__Plan) -> str:
    if plan.date_iso and plan.hour: return f'{plan.date_iso} {plan.hour}:00'
    if plan.date_iso:               return plan.date_iso
    return 'all dates'


def sync_plain(plan : Schema__CF__Sync__Plan, result=None) -> str:
    out = ['Sync · raw-cf-logs',
           f's3://{plan.bucket}/{plan.prefix}  scope={_scope(plan)}',
           f'remote={plan.remote_count} local={plan.local_count} missing={plan.missing_count} '
           f'(local={human_size(plan.present_bytes)} to_fetch={human_size(plan.missing_bytes)})']
    if result is not None and result.done:
        out.append(f'downloaded={result.downloaded} skipped={result.skipped} failed={result.failed} bytes={human_size(result.bytes)}')
    for f in plan.files:
        out.append(f'  {"OK " if f.present_local else "-- "}{f.key.rsplit("/", 1)[-1]}  {human_size(f.size)}')
    return '\n'.join(out)


def cache_plain(stats : Schema__CF__Local__Stats) -> str:
    out = ['Local Cache · raw-cf-logs', stats.base_path]
    if not stats.exists or stats.total_files == 0:
        out.append('empty — nothing synced yet')
        return '\n'.join(out)
    out.append(f'files={stats.total_files} size={human_size(stats.total_bytes)} '
               f'days={stats.day_count} hours={stats.hour_count} coverage={stats.first_day}..{stats.last_day}')
    for d in stats.days:
        out.append(f'  {d.day}  files={d.files}  size={human_size(d.bytes)}  hours={d.hours}')
    return '\n'.join(out)
