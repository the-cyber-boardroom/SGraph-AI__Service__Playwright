# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/screens: Tui_Api__Loadout__Modal
# A reusable ModalScreen for choosing which TUI APIs (and at which capability) a chat
# may use. One row per registered API; space cycles off → read → write → * ; Enter
# returns a Schema__Tui_Api__Loadout, Esc cancels. The model never opens this — it is
# a human/host decision (decision #10). Pure-ish: build_loadout() has no Textual deps.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.screen  import ModalScreen
from textual.widgets import Static

from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.List__Tui_Api__Grant     import List__Tui_Api__Grant
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Grant   import Schema__Tui_Api__Grant
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Loadout import Schema__Tui_Api__Loadout
from sgraph_ai_service_playwright__cli.tui.tool_api.schemas.Schema__Tui_Api__Scope   import Schema__Tui_Api__Scope

_CYCLE = ['off', 'read', 'write', '*']


class Tui_Api__Loadout__Modal(ModalScreen):
    BINDINGS = [('up',     'cursor_up',   'Up'),
                ('down',   'cursor_down', 'Down'),
                ('space',  'cycle',       'Cycle tier'),
                ('enter',  'apply',       'Apply'),
                ('escape', 'cancel',      'Cancel')]

    CSS = """
    Tui_Api__Loadout__Modal { align: center middle; }
    #loadout { width: auto; height: auto; padding: 1 2; border: round $accent; background: $panel; }
    """

    def __init__(self, registry, current: Schema__Tui_Api__Loadout = None):
        super().__init__()
        self.slugs    = registry.list_slugs()
        self.state    = {slug: 'off' for slug in self.slugs}
        self.selected = 0
        if current:                                                               # seed from the active loadout's grants
            for grant in current.grants:
                api, capability = str(grant.scope.api), str(grant.scope.capability)
                if api in self.state:
                    self.state[api] = capability if capability in _CYCLE else '*'

    def compose(self):
        yield Static(self._markup(), id='loadout')

    def _markup(self) -> str:
        lines = ['[bold]choose tools for this chat[/]', '', f'  [dim]{"api":<28}granted[/]']
        for index, slug in enumerate(self.slugs):
            marker = '[cyan]▸[/]' if index == self.selected else ' '
            tier   = self.state[slug]
            shown  = '[dim]off[/]' if tier == 'off' else f'[green]{tier}[/]'
            lines.append(f' {marker} {slug:<28}{shown}')
        if not self.slugs:
            lines.append('  [dim](no tools available — the chat registered none)[/]')
        lines += ['', '[dim]↑/↓ move · space cycle (off→read→write→*) · Enter apply · Esc cancel[/]']
        return '\n'.join(lines)

    def _rerender(self):
        self.query_one('#loadout', Static).update(self._markup())

    def cycle_current(self) -> None:                                              # pure: advance the highlighted API's tier
        if not self.slugs:
            return
        slug = self.slugs[self.selected]
        self.state[slug] = _CYCLE[(_CYCLE.index(self.state[slug]) + 1) % len(_CYCLE)]

    def build_loadout(self) -> Schema__Tui_Api__Loadout:                          # pure: state → loadout (no Textual)
        grants = List__Tui_Api__Grant()
        for slug, tier in self.state.items():
            if tier != 'off':
                grants.append(Schema__Tui_Api__Grant(scope=Schema__Tui_Api__Scope(api=slug, capability=tier)))
        loadout = Schema__Tui_Api__Loadout()
        loadout.grants = grants
        return loadout

    def action_cursor_down(self):
        if self.slugs:
            self.selected = min(self.selected + 1, len(self.slugs) - 1)
            self._rerender()

    def action_cursor_up(self):
        if self.slugs:
            self.selected = max(self.selected - 1, 0)
            self._rerender()

    def action_cycle(self):
        self.cycle_current()
        self._rerender()

    def action_apply(self):
        self.dismiss(self.build_loadout())

    def action_cancel(self):
        self.dismiss(None)
