# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — tui/tool_api/screens: Tui_Api__Explorer
# A Swagger-style TUI API explorer, built from Textual's own widgets (Header / Footer
# / DataTable / Static). Lists every registered provider's actions; highlighting shows
# the action's schema + scope; Enter (or 'i') invokes it THROUGH the execution center
# (so sequencing / gating / audit apply exactly as for the chat). No business logic
# here — it renders the registry and routes keys, mirroring the house TUI pattern.
# Tested headless via App.run_test() with an in-memory provider (no AWS, no mocks).
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app        import App, ComposeResult
from textual.binding    import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets    import DataTable, Footer, Header, Static

from sgraph_ai_service_playwright__cli.tui.tool_api.screens.Tui_Api__Explorer__Render import Tui_Api__Explorer__Render
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center import Tui_Api__Execution_Center
from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry         import Tui_Api__Registry


class Tui_Api__Explorer(App):
    TITLE = 'TUI API Explorer'
    CSS = """
    #actions  { width: 48%; }
    #panes    { height: 1fr; }
    #detail   { padding: 1; }
    #result   { padding: 1; border-top: solid $accent; }
    """
    BINDINGS = [Binding('i',      'invoke', 'Invoke'),
                Binding('ctrl+q', 'quit',   'Quit')]

    def __init__(self, registry: Tui_Api__Registry):
        super().__init__()
        self.registry    = registry
        self.center      = Tui_Api__Execution_Center(registry=registry)
        self.renderer    = Tui_Api__Explorer__Render()
        self.current       = None                                                 # (slug, action_name) under the cursor
        self.detail_markup = ''                                                   # last rendered detail (exposed for tests)
        self.last_result   = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id='panes'):
            yield DataTable(id='actions', cursor_type='row')
            with VerticalScroll():
                yield Static(id='detail')
                yield Static(id='result')
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one('#actions', DataTable)
        table.add_columns('api', 'action', 'tier')
        rows = self.renderer.action_rows(self.registry)
        for slug, name, tier, _description in rows:
            table.add_row(slug, name, tier, key=f'{slug}|{name}')
        if rows:
            self.current = (rows[0][0], rows[0][1])
            self._show_detail()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key and event.row_key.value:
            self.current = tuple(event.row_key.value.split('|', 1))
            self._show_detail()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key and event.row_key.value:
            self.current = tuple(event.row_key.value.split('|', 1))
            self.action_invoke()

    def action_invoke(self) -> None:
        if not self.current:
            return
        slug, name = self.current
        self.last_result = self.center.execute(slug, name, {})                    # empty params; a params form is a later enhancement
        self.query_one('#result', Static).update(self.renderer.result_markup(self.last_result))

    def _show_detail(self) -> None:
        slug, name = self.current
        provider   = self.registry.get(slug)
        action     = provider.action(name) if provider else None
        if action is not None:
            self.detail_markup = self.renderer.action_detail_markup(slug, action)
            self.query_one('#detail', Static).update(self.detail_markup)
