# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Traffic__Render
# Screen 5 (Traffic Reality) content as a Rich-markup string. PURE — no textual, no
# rich import — so the content is unit-testable on 3.11; the Textual screen drops it
# into a Static. Answers "what is going on on the website": throughput, bot vs human,
# top URIs, status mix, geography, cache. Every number traces to the snapshot; with
# no events the panels render zeros, never invented traffic.
# ═══════════════════════════════════════════════════════════════════════════════

import datetime

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Traffic_Snapshot import Schema__CF_TUI__Traffic_Snapshot
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.widgets.CF_TUI__Glyphs import sparkline, bar, pct, status_style


def traffic_markup(snapshot : Schema__CF_TUI__Traffic_Snapshot) -> str:
    lines = []
    stamp = datetime.datetime.fromtimestamp(int(snapshot.captured_at), datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    total = snapshot.total_events

    lines.append(f'[bold]CF Traffic Reality[/]   source=[cyan]{snapshot.source}[/]  [dim]{snapshot.source_label}[/]')
    lines.append(f'[dim]{stamp}  ·  {snapshot.files_sampled} object(s)  ·  {total} event(s)  ·  {snapshot.lines_skipped} skipped[/]')
    lines.append('')

    spark = sparkline([p.value for p in snapshot.throughput])
    lines.append('[bold]THROUGHPUT[/]  [dim](events / minute)[/]')
    lines.append(f'  [green]{spark}[/]' if spark else '  [dim](no events)[/]')
    lines.append('')

    lines.append('[bold]BOT vs HUMAN[/]')
    lines.append(_ratio_row('bot',     snapshot.bot_events,     total, 'red'))
    lines.append(_ratio_row('human',   snapshot.human_events,   total, 'green'))
    if snapshot.unknown_events:
        lines.append(_ratio_row('unknown', snapshot.unknown_events, total, 'dim'))
    lines.append('')

    lines.append('[bold]STATUS[/]')
    if not snapshot.status_classes:
        lines.append('  [dim](none)[/]')
    for row in snapshot.status_classes:
        style = status_style(row.label)
        lines.append(f'  [{style}]{row.label}[/]  {bar(row.count / total if total else 0, 8)} {row.count}')
    lines.append('')

    lines.append('[bold]CACHE[/]')
    lines.append(f'  hit  {bar(snapshot.cache_hits / total if total else 0, 8)} {snapshot.cache_hits} [dim]({pct(snapshot.cache_hits, total)}%)[/]')
    lines.append(f'  other {bar(snapshot.cache_other / total if total else 0, 8)} {snapshot.cache_other}')
    lines.append('')

    lines.append(f'[bold]TOP URIs[/]  ({len(snapshot.top_uris)})')
    _append_count_rows(lines, snapshot.top_uris, 40)
    lines.append('')

    lines.append(f'[bold]GEOGRAPHY[/]  ({len(snapshot.top_countries)})')
    _append_count_rows(lines, snapshot.top_countries, 12)
    lines.append('')

    lines.append(f'[bold]TOP BOTS[/]  ({len(snapshot.top_bots)})')
    _append_count_rows(lines, snapshot.top_bots, 40)

    return '\n'.join(lines)


def _ratio_row(label : str, part : int, whole : int, style : str) -> str:
    return f'  [{style}]{label.ljust(8)}[/] {bar(part / whole if whole else 0)} {part} [dim]({pct(part, whole)}%)[/]'


def _append_count_rows(lines : list, rows, label_width : int) -> None:
    if not rows:
        lines.append('  [dim](none)[/]')
        return
    for row in rows:
        lines.append(f'  {row.label[:label_width].ljust(label_width)} [dim]{row.count}[/]')
