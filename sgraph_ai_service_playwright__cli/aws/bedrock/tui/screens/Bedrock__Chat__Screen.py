# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — bedrock tui: Bedrock__Chat__Screen
# The chat App. Thin view (framework carve-out): a transcript of Chat__Bubbles + a
# docked Chat__Composer + a docked Chat__Cost__Meter. All logic + cost live in the
# injected Bedrock__Chat__Engine; this class only mounts widgets, streams deltas into
# the assistant bubble (via a worker so the blocking Bedrock call never freezes the
# UI), and binds keys. Cost is always visible; the per-call cap gates every send.
# ═══════════════════════════════════════════════════════════════════════════════

import asyncio
from pathlib import Path

from textual            import work, on
from textual.app        import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets    import Header, Footer

from sgraph_ai_service_playwright__cli.aws.bedrock.tui.bedrock_chat_tui__config              import (TITLE, PROVIDER,
                                                                                                     BUDGET_WARN_FRACTION)
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Render          import (turn_footer,
                                                                                                      streaming_footer,
                                                                                                      model_picker_rows)
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.widgets.Chat__Bubble           import Chat__Bubble
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.widgets.Chat__Composer         import Chat__Composer
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.widgets.Chat__Cost__Meter      import Chat__Cost__Meter
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.widgets.Chat__Doc__Chips        import Chat__Doc__Chips
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.widgets.Chat__Inspector        import Chat__Inspector
from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.widgets.Chat__Vfs__Browser      import Chat__Vfs__Browser

COST_OVERRIDE_CONFIRMED = 1e9                                                      # explicit user-confirmed over-cap send


class Bedrock__Chat__Screen(App):
    TITLE    = TITLE
    # The composer (TextArea) keeps focus for typing, so global actions use Ctrl-combos
    # / F1 that TextArea does not consume — they bubble past the composer to the App.
    BINDINGS = [('ctrl+q',   'leave',        'Quit'),
                ('f1',       'help',         'Help'),
                ('f2',       'inspector',    'Inspect'),
                ('f3',       'vfs',          'Files'),
                ('ctrl+t',   'toggle_theme', 'Theme'),
                ('ctrl+s',   'export_card',  'Export'),
                ('ctrl+o',   'model',        'Model'),
                ('ctrl+b',   'brief',        'Brief'),
                ('ctrl+g',   'tools',        'Tools'),
                ('ctrl+d',   'attach',       'Attach doc'),
                ('ctrl+l',   'clear',        'Clear'),
                ('ctrl+up',  'inspect_prev', 'Prev req'),
                ('ctrl+down','inspect_next', 'Next req'),
                ('escape',   'stop',         'Stop')]

    def __init__(self, engine, region: str = '', model_alias: str = 'default',
                 context=None, brief_dir: str = '',
                 registry=None, center=None, tool_config=None, name_map=None):
        super().__init__()
        self.engine            = engine
        self.session           = engine.new_session(region=region, model_alias=model_alias, context=context)
        self.brief_dir         = brief_dir or str(Path.home() / '.sg' / 'aws' / 'bedrock' / 'chat')
        self.exited            = False
        self.last_turn         = None
        self.inspector_selected = 0
        self.vfs_selected      = 0
        self.registry          = registry                                         # the tools the chat consumes (when tool-enabled)
        self.center            = center
        self.tool_config       = tool_config
        self.name_map          = name_map or {}
        self.tools_active      = bool(tool_config and tool_config.get('tools'))    # tools loaded → agentic (non-streaming) path
        self.pending_docs      = []                                               # documents attached to the next message (^D)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield VerticalScroll(id='transcript')
            yield Chat__Inspector(id='inspector')
            yield Chat__Vfs__Browser(id='vfs')
            yield Chat__Cost__Meter(id='meter')
        yield Chat__Doc__Chips(id='chips')
        yield Chat__Composer(id='composer')
        yield Footer()

    def on_mount(self) -> None:
        self.inspector().display   = False                                        # hidden until f2; cost meter shown by default
        self.vfs_browser().display = False                                        # hidden until f3
        self.chips().display       = False
        self.meter().refresh_from(self.session)
        self.query_one('#composer', Chat__Composer).focus()

    # ── handles ────────────────────────────────────────────────────────────────

    def transcript(self) -> VerticalScroll:
        return self.query_one('#transcript', VerticalScroll)

    def meter(self) -> Chat__Cost__Meter:
        return self.query_one('#meter', Chat__Cost__Meter)

    def inspector(self) -> Chat__Inspector:
        return self.query_one('#inspector', Chat__Inspector)

    def chips(self) -> Chat__Doc__Chips:
        return self.query_one('#chips', Chat__Doc__Chips)

    def vfs_browser(self) -> Chat__Vfs__Browser:
        return self.query_one('#vfs', Chat__Vfs__Browser)

    # ── send flow ────────────────────────────────────────────────────────────────

    @on(Chat__Composer.Submitted)                                                 # bind by type — the Chat__Composer name mangles the auto handler
    def _on_submitted(self, message: Chat__Composer.Submitted) -> None:
        self.handle_submit(message.text)

    def handle_submit(self, text: str, cost_override: float = None) -> None:
        if self.tools_active:                                                     # tool-enabled chat → agentic (non-streaming) loop
            self.agentic_worker(text)
            return
        try:
            self.engine.preflight_cost(self.session, text, cost_override)         # leaves session clean if it trips
        except ValueError as exc:
            from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Cost__Confirm import Bedrock__Chat__Cost__Confirm
            def after(ok: bool) -> None:
                if ok:
                    self.handle_submit(text, cost_override=COST_OVERRIDE_CONFIRMED)
            self.push_screen(Bedrock__Chat__Cost__Confirm(str(exc)), after)
            return
        self.converse_worker(text, cost_override)

    @work(exclusive=True, group='llm')
    async def converse_worker(self, text: str, cost_override: float) -> None:
        user = Chat__Bubble('user', text, author='you')
        await self.transcript().mount(user)
        bubble = Chat__Bubble('assistant', '', author=str(self.session.model_alias))
        await self.transcript().mount(bubble)
        bubble.set_footer(streaming_footer())
        self.transcript().anchor()

        acc = []
        def on_delta(chunk: str) -> None:
            acc.append(chunk)
            self.call_from_thread(bubble.set_body, ''.join(acc))

        documents = self.take_pending_docs()
        turn = await asyncio.to_thread(self.engine.send_turn, self.session, text, on_delta, cost_override, documents)
        bubble.set_body(''.join(acc))
        self.finish_turn(bubble, turn)

    @work(exclusive=True, group='llm')
    async def agentic_worker(self, text: str) -> None:                            # tool-enabled: non-streaming Converse tool loop
        from textual.widgets import Static
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.widgets.Chat__Tool_Calls import Chat__Tool_Calls

        await self.transcript().mount(Chat__Bubble('user', text, author='you'))
        status = Static('[dim]⟳ running tools…[/]')
        await self.transcript().mount(status)
        self.transcript().anchor()

        documents = self.take_pending_docs()
        turn = await asyncio.to_thread(self.engine.send_turn_agentic, self.session, text,
                                       self.registry, self.center, self.tool_config, self.name_map,
                                       documents=documents)
        await status.remove()
        if turn.tool_log:                                                         # collapsed tool-call card (request/response on expand)
            await self.transcript().mount(Chat__Tool_Calls(list(turn.tool_log)))
        bubble = Chat__Bubble('assistant', '', author=str(self.session.model_alias))
        await self.transcript().mount(bubble)
        bubble.set_body(turn.response_text or '(no response)')
        self.finish_turn(bubble, turn)

    def finish_turn(self, bubble: Chat__Bubble, turn) -> None:
        self.last_turn = turn
        bubble.set_footer(turn_footer(turn.input_tokens, turn.output_tokens, turn.cost_usd, turn.latency_ms,
                                      getattr(turn, 'model_calls', 1), getattr(turn, 'tool_calls', 0)))
        self.meter().refresh_from(self.session)
        if self.inspector().display:                                              # follow the newest request while inspecting
            self.inspector_selected = len(self.session.turns) - 1
            self.inspector().refresh_from(self.session, self.inspector_selected)
        if self.vfs_browser().display:                                            # the agent may have written files this turn
            self.vfs_browser().refresh_from(self._vfs_provider(), self.vfs_selected)
        self.transcript().anchor()
        frac = (self.session.total_cost_usd / self.session.budget_usd) if self.session.budget_usd else 0.0
        if frac >= BUDGET_WARN_FRACTION:
            self.notify(f'session cost ${self.session.total_cost_usd:.4f} of ${self.session.budget_usd:.2f} budget',
                        severity='warning')

    # ── right-panel slot: cost meter · inspector (f2) · VFS browser (f3) ──────────

    def _show_panel(self, panel: str) -> None:                                    # exactly one of 'meter' | 'inspector' | 'vfs' is visible
        self.meter().display       = (panel == 'meter')
        self.inspector().display   = (panel == 'inspector')
        self.vfs_browser().display = (panel == 'vfs')

    def action_inspector(self) -> None:                                           # f2 — request/response inspector
        if self.inspector().display:
            self._show_panel('meter')
            return
        self._show_panel('inspector')
        self.inspector_selected = max(0, len(self.session.turns) - 1)
        self.inspector().refresh_from(self.session, self.inspector_selected)

    def action_vfs(self) -> None:                                                 # f3 — VFS file browser (uses the same slot as the inspector)
        if self.vfs_browser().display:
            self._show_panel('meter')
            return
        self._show_panel('vfs')
        self.vfs_selected = 0
        self.vfs_browser().refresh_from(self._vfs_provider(), self.vfs_selected)

    def _vfs_provider(self):                                                      # the chat's VFS provider, if tools are enabled
        return self.registry.get('core.vfs') if self.registry is not None else None

    def action_inspect_prev(self) -> None:
        self._vfs_step(-1) if self.vfs_browser().display else self._inspect_step(-1)

    def action_inspect_next(self) -> None:
        self._vfs_step(+1) if self.vfs_browser().display else self._inspect_step(+1)

    def _inspect_step(self, delta: int) -> None:
        if not self.inspector().display or not self.session.turns:
            return
        self.inspector_selected = max(0, min(self.inspector_selected + delta, len(self.session.turns) - 1))
        self.inspector().refresh_from(self.session, self.inspector_selected)

    def _vfs_step(self, delta: int) -> None:
        provider = self._vfs_provider()
        files    = list(provider.state().get('files', [])) if provider is not None else []
        if not files:
            return
        self.vfs_selected = max(0, min(self.vfs_selected + delta, len(files) - 1))
        self.vfs_browser().refresh_from(provider, self.vfs_selected)

    # ── actions ──────────────────────────────────────────────────────────────────

    def action_model(self) -> None:
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Model__Picker import Bedrock__Chat__Model__Picker
        aliases = ['default'] + self.engine.resolver.list_aliases(PROVIDER)
        rows    = model_picker_rows(aliases,
                                    self.engine.calc.pricing_for,
                                    lambda alias: self.engine.resolver.resolve(PROVIDER, alias, self.session.region))
        def after(alias: str) -> None:
            if alias:
                self.session.model_alias = alias
                self.meter().refresh_from(self.session)
                self.notify(f'model → {alias}')
        self.push_screen(Bedrock__Chat__Model__Picker(rows, current=str(self.session.model_alias)), after)

    def action_brief(self) -> None:
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Brief__Builder import Bedrock__Chat__Brief__Builder
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Brief__Modal   import Bedrock__Chat__Brief__Modal
        if self.session.turn_count == 0:
            self.notify('nothing to capture yet', severity='warning')
            return
        brief_text = Bedrock__Chat__Brief__Builder().build(self.session)
        write_path = str(Path(self.brief_dir) / f'brief-{self.session.session_id}.md')
        self.push_screen(Bedrock__Chat__Brief__Modal(brief_text, write_path))

    def action_attach(self) -> None:                                              # ctrl+d — attach a document to the next message
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Doc__Picker import Bedrock__Chat__Doc__Picker
        def after(document) -> None:
            if document is not None:
                self.pending_docs.append(document)
                self.chips().refresh_from(self.pending_docs)
                self.notify(f'attached {document.name} ({document.size}B)')
        self.push_screen(Bedrock__Chat__Doc__Picker(), after)

    def take_pending_docs(self) -> list:                                          # consume the pending attachments for this send
        documents = list(self.pending_docs)
        if documents:
            self.pending_docs = []
            self.chips().refresh_from([])
        return documents

    def action_tools(self) -> None:                                               # ctrl+g — choose which TUI APIs this chat may use
        from sgraph_ai_service_playwright__cli.tui.tool_api.screens.Tui_Api__Loadout__Modal import Tui_Api__Loadout__Modal
        registry = self._available_registry()
        def after(loadout) -> None:
            if loadout is not None:
                self.apply_loadout(registry, loadout)
        self.push_screen(Tui_Api__Loadout__Modal(registry), after)

    def _available_registry(self):                                                # the providers the chat can enable (VFS core tool first)
        if self.registry is not None:
            return self.registry
        from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Registry import Tui_Api__Registry
        registry = Tui_Api__Registry()
        try:
            from sgraph_ai_service_playwright__cli.tui.tool_api.core.vfs.Vfs__Tui_Api__Provider import Vfs__Tui_Api__Provider
            registry.register(Vfs__Tui_Api__Provider())
        except Exception:
            pass                                                                  # memory_fs absent → no VFS tool offered
        return registry

    def apply_loadout(self, registry, loadout) -> None:
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.tui_api.Bedrock__Tool_Config__Builder import Bedrock__Tool_Config__Builder
        from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Execution_Center        import Tui_Api__Execution_Center
        from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Loadout__Assembler       import Tui_Api__Loadout__Assembler
        from sgraph_ai_service_playwright__cli.tui.tool_api.service.Tui_Api__Privilege__Resolver      import Tui_Api__Privilege__Resolver
        resolver              = Tui_Api__Privilege__Resolver()
        granted               = Tui_Api__Loadout__Assembler().granted_actions(loadout, registry, resolver)
        tool_config, name_map = Bedrock__Tool_Config__Builder().build(granted)
        self.registry     = registry
        self.center       = Tui_Api__Execution_Center(registry=registry, resolver=resolver)
        self.tool_config  = tool_config
        self.name_map     = name_map
        self.tools_active = bool(tool_config.get('tools'))
        count = len(tool_config.get('tools', []))
        self.notify(f'tools: {count} action(s) enabled' if count else 'tools disabled')

    def action_clear(self) -> None:
        # Clears the conversation + cost only. The VFS / tools (self.registry, self.center)
        # are deliberately untouched — files the agent created survive a clear.
        old = self.session
        self.session = self.engine.new_session(region=old.region, model_alias=str(old.model_alias),
                                               budget_usd=old.budget_usd)
        self.session.system_prompt = old.system_prompt                            # keep any seeded context
        self.session.context_label = old.context_label
        for child in list(self.transcript().children):
            child.remove()
        self.inspector_selected = 0
        self.meter().refresh_from(self.session)
        if self.inspector().display:
            self.inspector().refresh_from(self.session, self.inspector_selected)
        if self.vfs_browser().display:                                            # VFS persists; just re-render the panel
            self.vfs_browser().refresh_from(self._vfs_provider(), self.vfs_selected)

    def action_stop(self) -> None:
        self.workers.cancel_group(self, 'llm')

    def action_help(self) -> None:
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.screens.Bedrock__Chat__Help import Bedrock__Chat__Help
        self.push_screen(Bedrock__Chat__Help(self.help_lines()))

    def help_lines(self) -> list:
        seen, lines = set(), []
        for klass in type(self).__mro__:
            if not klass.__module__.startswith('sgraph_ai_service_playwright'):
                continue
            for binding in klass.__dict__.get('BINDINGS', []):
                if isinstance(binding, (tuple, list)):
                    key  = binding[0]
                    desc = binding[2] if len(binding) > 2 else binding[1]
                else:
                    key  = getattr(binding, 'key', '')
                    desc = getattr(binding, 'description', '') or getattr(binding, 'action', '')
                if key and key not in seen:
                    seen.add(key)
                    lines.append((key, desc))
        lines.append(('enter', 'Send (⇧Enter newline)'))
        return lines

    def action_toggle_theme(self) -> None:
        self.theme = 'textual-light' if self.theme == 'textual-dark' else 'textual-dark'

    def action_export_card(self) -> None:
        from sgraph_ai_service_playwright__cli.aws.bedrock.tui.service.Bedrock__Chat__Card import Bedrock__Chat__Card
        self.copy_to_clipboard(Bedrock__Chat__Card().render(self.session))
        self.notify('session card copied to clipboard (OSC-52)')

    def action_leave(self) -> None:
        self.exited = True
        self.exit()
