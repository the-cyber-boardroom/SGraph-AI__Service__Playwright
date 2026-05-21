# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Sync__Render
# Pure markup for the raw-cf-logs sync screen (+ a plain variant for no-TTY). No
# textual, no rich — testable on 3.11. Shows the S3-vs-local diff for a scope, a
# progress line while downloading, and the per-file ✓/✗ list. Reuses the shared
# Tui__Text helpers (component-first).
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Sync__Plan   import Schema__CF__Sync__Plan
from sgraph_ai_service_playwright__cli.tui.render.Tui__Text                       import esc, human_size


def _scope(plan : Schema__CF__Sync__Plan) -> str:
    if plan.date_iso and plan.hour: return f'{plan.date_iso} {plan.hour}:00'
    if plan.date_iso:               return plan.date_iso
    return 'all dates'


def sync_markup(plan : Schema__CF__Sync__Plan, result=None, busy : bool = False, max_rows : int = 200) -> str:
    lines = []
    lines.append('[bold]Sync · raw-cf-logs[/]')
    lines.append(f'[dim]s3://{esc(plan.bucket)}/{esc(plan.prefix)}  ·  scope: {esc(_scope(plan))}[/]')
    lines.append('[dim]g download missing · r refresh · d debug · q quit[/]')
    lines.append('')
    lines.append(f'  remote [bold]{plan.remote_count}[/]   '
                 f'local [green]{plan.local_count}[/]   '
                 f'missing [yellow]{plan.missing_count}[/]   '
                 f'[dim]({human_size(plan.present_bytes)} local / {human_size(plan.missing_bytes)} to fetch)[/]')
    if busy:
        done = (result.downloaded + result.failed) if result else 0
        lines.append(f'  [cyan]downloading… {done}/{plan.missing_count}[/]')
    elif result is not None and result.done:
        fail = f'  [red]{result.failed} failed[/]' if result.failed else ''
        lines.append(f'  [green]✓ synced {result.downloaded} · {human_size(result.bytes)}[/]   [dim]{result.skipped} already present[/]{fail}')
    elif plan.missing_count == 0 and plan.remote_count:
        lines.append('  [green]✓ complete — every object for this scope is local[/]')
    lines.append('')
    for f in plan.files[:max_rows]:
        glyph = '[green]✓[/]' if f.present_local else '[yellow]·[/]'
        name  = esc(f.key.rsplit('/', 1)[-1])
        lines.append(f'  {glyph} {name[:54].ljust(54)} [dim]{human_size(f.size).rjust(9)}[/]')
    if len(plan.files) > max_rows:
        lines.append(f'  [dim]… {len(plan.files) - max_rows} more[/]')
    return '\n'.join(lines)
