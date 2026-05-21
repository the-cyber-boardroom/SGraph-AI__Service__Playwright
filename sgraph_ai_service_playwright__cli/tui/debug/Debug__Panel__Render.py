# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui debug: Debug__Panel__Render
# Pure Rich-markup for the debug side panel — no textual import, so it is unit-tested
# on 3.11 without a terminal. Renders the tail of a Debug__Event_Log: one line per
# event (HH:MM:SS · category · message), errors in red, optional detail dimmed. The
# Debug__Panel widget just drops this string into a Static.
# ═══════════════════════════════════════════════════════════════════════════════

from sgraph_ai_service_playwright__cli.tui.debug.Debug__Event_Log import Debug__Event_Log
from sgraph_ai_service_playwright__cli.tui.render.Tui__Text       import esc, hhmmss

CAT_STYLE = {'s3.list'      : 'cyan',
             's3.get'       : 'green',
             'fs.write'     : 'yellow',
             'fs.read'      : 'blue',
             'aws.firehose' : 'magenta',
             'aws.cf'       : 'magenta',
             'aws.logs'     : 'magenta',
             'ui'           : 'dim'}


def debug_panel_markup(event_log : Debug__Event_Log, max_lines : int = 200) -> str:
    events = event_log.tail(max_lines)
    lines  = [f'[bold]Debug[/]  [dim]({event_log.count()} events · d toggles)[/]', '']
    if not events:
        lines.append('[dim](no activity yet)[/]')
        return '\n'.join(lines)
    for e in events:
        cat_style = CAT_STYLE.get(e.category, 'white')
        glyph     = '[red]✗[/]' if not e.ok else '[dim]·[/]'
        cat       = f'[{cat_style}]{esc(e.category)}[/]'
        msg       = f'[red]{esc(e.message)}[/]' if not e.ok else esc(e.message)
        lines.append(f'{glyph} [dim]{hhmmss(e.ts)}[/] {cat}  {msg}')
        if e.detail:
            lines.append(f'    [dim]{esc(e.detail)}[/]')
    return '\n'.join(lines)
