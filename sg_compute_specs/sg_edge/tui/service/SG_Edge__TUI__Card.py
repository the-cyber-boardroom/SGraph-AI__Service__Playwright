# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Card
# Pure: render a snapshot as a plain-text ASCII card for the `r`/export action
# (picomon-style). No rich markup — the output is meant to be copied via OSC-52 or
# written to a file and pasted into an incident note. It states the pending panes
# explicitly so a shared card never implies data we do not have.
# ═══════════════════════════════════════════════════════════════════════════════

import datetime

from osbot_utils.type_safe.Type_Safe                                       import Type_Safe

from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State      import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.schemas.Schema__SG_Edge__TUI__Snapshot    import Schema__SG_Edge__TUI__Snapshot
from sg_compute_specs.sg_edge.tui.sg_edge_tui__config                       import TUI_CARD_WIDTH

STATE_GLYPH = {Enum__SG_Edge__TUI__Slug_State.LIVE          : '●',
               Enum__SG_Edge__TUI__Slug_State.DORMANT       : '◐',
               Enum__SG_Edge__TUI__Slug_State.ORPHAN_BACKEND: '✗'}


class SG_Edge__TUI__Card(Type_Safe):
    width : int = TUI_CARD_WIDTH

    def render(self, snapshot : Schema__SG_Edge__TUI__Snapshot) -> str:
        W     = self.width
        lines = []

        def row(text=''):
            lines.append('│ ' + text[:W].ljust(W) + ' │')

        def rule(left, right):
            lines.append(left + '─' * (W + 2) + right)

        yn    = lambda ok: '✓' if ok else '✗'
        stamp = datetime.datetime.fromtimestamp(int(snapshot.captured_at), datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

        rule('┌', '┐')
        row(f'SG/Edge — {snapshot.target}   ({snapshot.parent})')
        row(stamp)
        rule('├', '┤')

        if not snapshot.zone_exists:
            row('not provisioned — no hosted zone')
            rule('└', '┘')
            return '\n'.join(lines)

        row('Browser  http://<slug>.' + snapshot.parent)
        row('  ▼')
        row(f'{yn(snapshot.wildcard)} Wildcard   *.{snapshot.parent}')
        row('  ▼')
        row(f'{yn(len(snapshot.fleet_ips) > 0)} Proxy fleet  ({len(snapshot.fleet_ips)} IP)')
        for ip in snapshot.fleet_ips:
            row(f'    • {ip}')
        row('  ▼')
        row(f'Slugs  ({len(snapshot.slugs)})')
        if not snapshot.slugs:
            row('    (none registered)')
        for slug in snapshot.slugs:
            glyph   = STATE_GLYPH.get(slug.state, '·')
            backend = f' → {slug.backend_ip}:{slug.backend_port}' if slug.state == Enum__SG_Edge__TUI__Slug_State.LIVE else ''
            row(f'    {glyph} {slug.slug[:18].ljust(18)} {str(slug.state)}{backend}')
        rule('├', '┤')
        row('pending (Slice 5): cost · throughput · instances')
        rule('└', '┘')

        if snapshot.issues:
            lines.append('')
            lines.append('Checks:')
            for issue in snapshot.issues:
                lines.append(f'  [{str(issue.severity)}] {issue.area}  {issue.message}')
        return '\n'.join(lines)
