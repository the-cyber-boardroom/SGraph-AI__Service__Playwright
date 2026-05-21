# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Files__Render
# The S3-browser-for-CF-logs content as Rich-markup strings. PURE — no textual, no
# rich import — so it is unit-testable on 3.11; the Textual screen drops these into a
# Static. Two views: a per-day file list (browse) and one file's parsed contents
# (visual rows) with a raw-TSV toggle. Every row traces to listed/parsed data.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__File_View import Schema__CF_TUI__File_View
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.widgets.CF_TUI__Glyphs import status_style


def human_size(n : int) -> str:
    if n < 1024:               return f'{n}B'
    if n < 1024 * 1024:        return f'{n / 1024:.1f}KB'
    return f'{n / (1024 * 1024):.1f}MB'


def _esc(text : str) -> str:                                                         # escape Rich markup so raw log content can't open a tag
    return text.replace('[', r'\[')


def files_browse_markup(rows, selected_index : int = 0, scope_label : str = '') -> str:
    lines = []
    lines.append(f'[bold]CF Log Files[/]   [dim]{scope_label}[/]   ({len(rows)})')
    lines.append('[dim]↑/↓ select · Enter open · r refresh · q quit[/]')
    lines.append('')
    if not rows:
        lines.append('  [dim](no files)[/]')
        return '\n'.join(lines)
    for i, row in enumerate(rows):
        marker   = '[cyan]▸[/]' if i == selected_index else ' '
        basename = row.key.rsplit('/', 1)[-1]
        when     = row.delivery_iso or row.last_modified or ''
        style    = 'bold' if i == selected_index else 'default'
        lines.append(f' {marker} [{style}]{basename[:46].ljust(46)}[/] [dim]{human_size(row.size_bytes).rjust(8)}  {when}[/]')
    return '\n'.join(lines)


def files_browse_plain(rows, scope_label : str = '') -> str:                         # no-TTY fallback: plain text listing
    out = [f'CF Log Files   {scope_label}   ({len(rows)})']
    if not rows:
        out.append('  (no files)')
        return '\n'.join(out)
    for row in rows:
        basename = row.key.rsplit('/', 1)[-1]
        when     = row.delivery_iso or row.last_modified or ''
        out.append(f'  {basename[:46].ljust(46)} {human_size(row.size_bytes).rjust(8)}  {when}')
    return '\n'.join(out)


def file_view_markup(view : Schema__CF_TUI__File_View, raw : bool = False) -> str:
    lines    = []
    basename = view.key.rsplit('/', 1)[-1]
    mode     = 'raw TSV' if raw else 'parsed'
    lines.append(f'[bold]{_esc(basename)}[/]   [dim]{human_size(view.size_bytes)} · {view.total_events} event(s) · {view.lines_skipped} skipped · [{mode}][/]')
    lines.append('[dim]t raw/parsed · Esc back · q quit[/]')
    lines.append('')

    if raw:
        if not view.raw_text.strip():
            lines.append('  [dim](empty)[/]')
        for raw_line in view.raw_text.split('\n'):
            lines.append(f'[dim]{_esc(raw_line)}[/]')
        return '\n'.join(lines)

    if not view.events:
        lines.append('  [dim](no events)[/]')
        return '\n'.join(lines)
    lines.append('[dim]  time      method status uri                              cc cache bot ua[/]')
    for ev in view.events:
        cache = '[green]hit[/] ' if ev.cache_hit else '[dim]miss[/]'
        bot   = '[red]bot[/]  ' if ev.is_bot else '[green]human[/]'
        st    = status_style(ev.status_class)
        lines.append(f'  {ev.time}  {ev.method[:6].ljust(6)} [{st}]{str(ev.status).ljust(3)}[/]    '
                     f'{ev.uri[:32].ljust(32)} {ev.country[:2].ljust(2)} {cache} {bot} [dim]{_esc(ev.user_agent[:24])}[/]')
    return '\n'.join(lines)
