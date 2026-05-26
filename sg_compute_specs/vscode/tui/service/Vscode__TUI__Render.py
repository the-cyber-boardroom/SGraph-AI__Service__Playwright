# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — vscode tui: Vscode__TUI__Render
# Pure markup builder for the stacks dashboard. Imports neither Textual nor Rich —
# it emits a Rich-markup string the screen drops into a Static. Unit-tested alone.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe                                 import Type_Safe

from sg_compute_specs.vscode.tui.schemas.Schema__Vscode__TUI__Snapshot import Schema__Vscode__TUI__Snapshot

_STATE_COLOUR = {'running': 'green', 'pending': 'yellow', 'stopping': 'yellow',
                 'stopped': 'red', 'shutting-down': 'red', 'terminated': 'red'}


def _esc(text: str) -> str:                                                          # neutralise Rich markup in untrusted field values
    return str(text).replace('[', r'\[')


class Vscode__TUI__Render(Type_Safe):

    def stacks_markup(self, snapshot: Schema__Vscode__TUI__Snapshot) -> str:
        lines = [f'[bold]VS Code stacks[/]  ·  region [cyan]{_esc(snapshot.region)}[/]  '
                 f'[dim]({snapshot.total})[/]', '']
        if not snapshot.stacks:
            lines.append('  [dim]no vscode stacks — sg vscode create[/]')
            return '\n'.join(lines)
        lines.append('  [bold]name              state     dist          ingress       url[/]')
        for s in snapshot.stacks:
            colour = _STATE_COLOUR.get(s.state, 'white')
            lines.append(f'  {_esc(s.stack_name):17.17} '
                         f'[{colour}]{s.state:9.9}[/] '
                         f'{_esc(s.distribution):13.13} '
                         f'{_esc(s.ingress):13.13} '
                         f'[cyan]{_esc(s.vscode_url)}[/]')
        lines.append('')
        lines.append('  [dim]r refresh · d debug · q quit · native: sg vscode list/forward/connect/delete[/]')
        if not snapshot.can_act:
            lines.append('  [yellow]read-only — mutations disabled[/]')
        return '\n'.join(lines)
