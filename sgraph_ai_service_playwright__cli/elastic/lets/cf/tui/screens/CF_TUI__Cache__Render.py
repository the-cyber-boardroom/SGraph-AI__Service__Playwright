# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Cache__Render
# Pure markup for the local raw-cf-logs cache stats (+ a plain variant). No textual,
# no rich — testable on 3.11. Shows totals, partition coverage, and a per-day table
# so "what do we have locally" is answerable at a glance (the optimisation baseline).
# Reuses the shared Tui__Text helpers (component-first).
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.elastic.lets.cf.local.schemas.Schema__CF__Local__Stats import Schema__CF__Local__Stats
from sgraph_ai_service_playwright__cli.tui.render.Tui__Text                       import esc, human_size, human_count


def cache_stats_markup(stats : Schema__CF__Local__Stats, max_days : int = 60) -> str:
    lines = []
    lines.append('[bold]Local Cache · raw-cf-logs[/]')
    lines.append(f'[dim]{esc(stats.base_path)}[/]')
    lines.append('[dim]r refresh · d debug · q quit[/]')
    lines.append('')
    if not stats.exists or stats.total_files == 0:
        lines.append('  [yellow]empty[/] — nothing synced yet. Run [bold]tui sync --mode download[/].')
        return '\n'.join(lines)
    lines.append(f'  files [bold]{human_count(stats.total_files)}[/]   '
                 f'size [bold]{human_size(stats.total_bytes)}[/]   '
                 f'days [bold]{stats.day_count}[/]   '
                 f'hours [bold]{stats.hour_count}[/]')
    lines.append(f'  [dim]coverage {esc(stats.first_day)} → {esc(stats.last_day)}[/]')
    lines.append('')
    lines.append('  [dim]day           files      size      hours[/]')
    for d in stats.days[:max_days]:
        lines.append(f'  {esc(d.day).ljust(12)}  {human_count(d.files).rjust(6)}  {human_size(d.bytes).rjust(9)}  {str(d.hours).rjust(5)}')
    if len(stats.days) > max_days:
        lines.append(f'  [dim]… {len(stats.days) - max_days} more days[/]')
    return '\n'.join(lines)


def cache_stats_plain(stats : Schema__CF__Local__Stats) -> str:
    out = ['Local Cache · raw-cf-logs', stats.base_path]
    if not stats.exists or stats.total_files == 0:
        out.append('empty — nothing synced yet')
        return '\n'.join(out)
    out.append(f'files={stats.total_files} size={human_size(stats.total_bytes)} '
               f'days={stats.day_count} hours={stats.hour_count} coverage={stats.first_day}..{stats.last_day}')
    for d in stats.days:
        out.append(f'  {d.day}  files={d.files}  size={human_size(d.bytes)}  hours={d.hours}')
    return '\n'.join(out)
