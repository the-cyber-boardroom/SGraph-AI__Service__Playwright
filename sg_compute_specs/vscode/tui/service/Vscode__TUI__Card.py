# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode tui: Vscode__TUI__Card
# Pure plain-text ASCII card — the non-TTY fallback (piped / CI) and the export
# surface. No Rich markup; safe to paste into a note.
# ═══════════════════════════════════════════════════════════════════════════════

import datetime

from osbot_utils.type_safe.Type_Safe                                 import Type_Safe

from sg_compute_specs.vscode.tui.schemas.Schema__Vscode__TUI__Snapshot import Schema__Vscode__TUI__Snapshot

CARD_WIDTH = 72


class Vscode__TUI__Card(Type_Safe):
    width : int = CARD_WIDTH

    def render(self, snapshot: Schema__Vscode__TUI__Snapshot) -> str:
        W     = self.width
        lines = []

        def row(text=''):
            lines.append('│ ' + str(text)[:W].ljust(W) + ' │')

        def rule(left, right):
            lines.append(left + '─' * (W + 2) + right)

        stamp = datetime.datetime.fromtimestamp(
            int(snapshot.captured_at) or 0, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        rule('┌', '┐')
        row(f'VS Code stacks — region {snapshot.region}   ({snapshot.total})')
        row(stamp)
        rule('├', '┤')
        if not snapshot.stacks:
            row('(none — sg vscode create)')
        for s in snapshot.stacks:
            row(f'{s.state[:7].ljust(7)} {s.stack_name[:20].ljust(20)} {s.distribution[:12].ljust(12)} {s.ingress}')
            if s.vscode_url:
                row(f'    {s.vscode_url}')
        rule('└', '┘')
        lines.append('')
        lines.append('native commands (the screen calls the same backend — never TUI-only):')
        for verb, cmd in (('list',    'sg vscode list'),
                          ('forward', 'sg vscode forward <name>'),
                          ('connect', 'sg vscode connect <name>'),
                          ('delete',  'sg vscode delete <name>')):
            lines.append(f'  {verb:<9} {cmd}')
        return '\n'.join(lines)
