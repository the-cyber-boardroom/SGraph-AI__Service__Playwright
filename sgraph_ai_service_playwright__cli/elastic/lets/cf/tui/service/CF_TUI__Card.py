# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — cf tui: CF_TUI__Card
# Pure: render a traffic snapshot as a plain-text ASCII card for the `r`/export
# action (picomon-style) and the no-TTY fallback. No rich markup — meant to be
# copied via OSC-52 or pasted into an incident note. States the source explicitly so
# a shared card never implies live traffic when it came from in-memory fixtures.
# ═══════════════════════════════════════════════════════════════════════════════

import datetime

from osbot_utils.type_safe.Type_Safe                                                import Type_Safe

from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.schemas.Schema__CF_TUI__Traffic_Snapshot import Schema__CF_TUI__Traffic_Snapshot
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.screens.widgets.CF_TUI__Glyphs import sparkline, pct
from sgraph_ai_service_playwright__cli.elastic.lets.cf.tui.cf_tui__config            import TUI_CARD_WIDTH


class CF_TUI__Card(Type_Safe):
    width : int = TUI_CARD_WIDTH

    def render(self, snapshot : Schema__CF_TUI__Traffic_Snapshot) -> str:
        W     = self.width
        lines = []
        total = snapshot.total_events

        def row(text=''):
            lines.append('│ ' + text[:W].ljust(W) + ' │')

        def rule(left, right):
            lines.append(left + '─' * (W + 2) + right)

        stamp = datetime.datetime.fromtimestamp(int(snapshot.captured_at), datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

        rule('┌', '┐')
        row(f'CF Traffic Reality — {snapshot.source}')
        row(snapshot.source_label)
        row(stamp)
        rule('├', '┤')
        row(f'{snapshot.files_sampled} object(s)  ·  {total} event(s)  ·  {snapshot.lines_skipped} skipped')
        row(f'throughput  {sparkline([p.value for p in snapshot.throughput])}')
        rule('├', '┤')
        row(f'bot     {snapshot.bot_events}  ({pct(snapshot.bot_events, total)}%)')
        row(f'human   {snapshot.human_events}  ({pct(snapshot.human_events, total)}%)')
        if snapshot.unknown_events:
            row(f'unknown {snapshot.unknown_events}  ({pct(snapshot.unknown_events, total)}%)')
        row(f'cache   hit {snapshot.cache_hits} / other {snapshot.cache_other}')
        rule('├', '┤')
        row('STATUS')
        for r in snapshot.status_classes:
            row(f'  {r.label}  {r.count}')
        row('TOP URIs')
        if not snapshot.top_uris:
            row('  (none)')
        for r in snapshot.top_uris:
            row(f'  {r.label[:46].ljust(46)} {r.count}')
        rule('└', '┘')
        return '\n'.join(lines)
