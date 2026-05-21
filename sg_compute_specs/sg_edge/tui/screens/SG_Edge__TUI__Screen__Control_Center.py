# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__Screen__Control_Center
# The action-capable cockpit over the local edge — the first SG/Edge screen to
# converge onto the shared cli/tui `Tui__App` (so the Debug Panel comes for free).
#
# It owns NO logic (separation guide): every action key is one call on the existing
# SG_Edge__TUI__Data_Source — the same backend the `sg edge local *` commands use.
# Actions are capability-gated (source.can_act(): local True, AWS False → greyed, the
# keypress never raises); destructive ones (u / X) require a y/n confirm; `request`
# is a read-only simulate; every call is logged to the shared Debug Panel.
#
# Layout: left = STATE (markup) + a DataTable slug inventory (select → target);
# right = a slug Input + the ACTIONS surface + a live PREVIEW; far right = Debug Panel.
# Carries `?` help / `e` OSC-52 export / `t` theme from the SG/Edge base (added locally
# for now — lift into Tui__App in a coordinated shared-lib change later).
# ═══════════════════════════════════════════════════════════════════════════════

from textual.binding    import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets    import Header, Footer, Static, DataTable, Input

from sgraph_ai_service_playwright__cli.tui.components.Tui__App                       import Tui__App
from sgraph_ai_service_playwright__cli.tui.components.Debug__Panel                   import Debug__Panel
from sg_compute_specs.sg_edge.tui.enums.Enum__SG_Edge__TUI__Slug_State              import Enum__SG_Edge__TUI__Slug_State
from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Control__Render             import (
    control_state_markup, control_actions_markup, control_preview_markup)

LIVE        = Enum__SG_Edge__TUI__Slug_State.LIVE
PENDING_MSG = 'pending Slice 5 (live EC2) — actions disabled on this target'


class SG_Edge__TUI__Screen__Control_Center(Tui__App):
    TITLE    = 'SG/Edge Control Center'
    CSS      = """
    #cc-left  { width: 2fr; padding: 0 1; }
    #cc-right { width: 1fr; padding: 0 1; }
    #cc-state { height: auto; }
    #cc-slugs { height: 1fr; }
    """
    BINDINGS = [Binding('n', 'register',         'register'),
                Binding('N', 'register_dormant', 'register dormant'),
                Binding('u', 'unregister',       'unregister'),
                Binding('g', 'request',          'request'),
                Binding('S', 'setup',            'setup'),
                Binding('X', 'teardown',         'teardown'),
                Binding('question_mark', 'help',         'Help'),
                Binding('e',             'export_card',  'Export'),
                Binding('t',             'toggle_theme', 'Theme')]

    def __init__(self, source, **kwargs):
        super().__init__(**kwargs)
        self.source   = source
        self.snapshot = None

    # ── layout ───────────────────────────────────────────────────────────────────
    def compose(self):
        yield Header()
        with Horizontal():
            with Vertical(id='cc-left'):
                yield Static('', id='cc-state')
                yield DataTable(id='cc-slugs', cursor_type='row', zebra_stripes=True)
            with Vertical(id='cc-right'):
                yield Input(placeholder='slug name…', id='cc-slug-input')
                yield Static('', id='cc-actions')
                yield Static('', id='cc-preview')
            yield Debug__Panel(self.debug_log, id='debug-panel')
        yield Footer()

    def on_mount(self) -> None:
        self.query_one('#cc-slugs', DataTable).add_columns('slug', 'state', 'backend')
        super().on_mount()                                                           # apply_debug_visibility + populate + refresh_debug + interval
        self.query_one('#cc-slugs', DataTable).focus()                               # focus the table so action keys (not the Input) fire

    # ── render (pure body) ─────────────────────────────────────────────────────────
    def populate(self) -> None:
        self.snapshot = self.source.snapshot()
        self.query_one('#cc-state',   Static).update(control_state_markup(self.snapshot))
        self.refill_slugs()
        self.query_one('#cc-actions', Static).update(control_actions_markup(self.source.can_act(), PENDING_MSG))
        self.refresh_preview()

    def refill_slugs(self) -> None:
        table  = self.query_one('#cc-slugs', DataTable)
        cursor = table.cursor_row
        table.clear()
        for slug in self.snapshot.slugs:
            backend = f'{slug.backend_ip}:{slug.backend_port}' if slug.state == LIVE else '—'
            table.add_row(slug.slug, str(slug.state), backend)
        if table.row_count:
            table.move_cursor(row=min(cursor, table.row_count - 1))

    def refresh_preview(self) -> None:
        if self.snapshot is not None:
            self.query_one('#cc-preview', Static).update(control_preview_markup(self.snapshot, self.target_slug()))

    # ── target resolution ──────────────────────────────────────────────────────────
    def target_slug(self) -> str:
        typed = self.query_one('#cc-slug-input', Input).value.strip()
        if typed:
            return typed
        return self.selected_slug()

    def selected_slug(self) -> str:
        slugs = self.snapshot.slugs if self.snapshot else []
        index = self.query_one('#cc-slugs', DataTable).cursor_row
        return slugs[index].slug if 0 <= index < len(slugs) else ''

    def on_input_changed(self, event) -> None:
        self.refresh_preview()

    def on_data_table_row_highlighted(self, event) -> None:
        self.refresh_preview()

    def on_input_submitted(self, event) -> None:                                     # Enter in the slug Input → register that name
        self.action_register()

    # ── action plumbing ────────────────────────────────────────────────────────────
    def guard(self) -> bool:
        if not self.source.can_act():
            self.notify(PENDING_MSG, severity='warning')
            return False
        return True

    def perform(self, name : str, slug : str, call) -> None:
        label = f'{name} {slug}'.strip()
        try:
            call()
            self.log_event('stack', label, 'ok', ok=True)
            self.notify(f'{label} ✓')
        except Exception as exc:                                                     # honest failure → debug + toast, never a crash
            self.log_event('stack', label, str(exc), ok=False)
            self.notify(f'{label} failed: {exc}', severity='error')
        self.populate()

    def confirm_then(self, message : str, name : str, slug : str, call) -> None:
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Confirm import SG_Edge__TUI__Confirm

        def resolved(ok : bool) -> None:
            if ok:
                self.perform(name, slug, call)
            else:
                self.notify(f'{name} cancelled')
        self.push_screen(SG_Edge__TUI__Confirm(message), resolved)

    # ── actions (each = one source call = one `sg edge local *` verb) ───────────────
    def action_register(self) -> None:
        if not self.guard():
            return
        slug = self.target_slug()
        if not slug:
            self.notify('type a slug name first')
            return
        self.perform('register', slug, lambda: self.source.register(slug))

    def action_register_dormant(self) -> None:
        if not self.guard():
            return
        slug = self.target_slug()
        if not slug:
            self.notify('type a slug name first')
            return
        self.perform('register-dormant', slug, lambda: self.source.register(slug, with_backend=False))

    def action_request(self) -> None:
        if not self.guard():                                                         # AWS source.request() raises until Slice 5 → gate it too
            return
        slug = self.target_slug()
        if not slug:
            self.notify('select or type a slug')
            return
        try:
            response = self.source.request(slug)
            self.log_event('stack', f'request {slug}', f'HTTP {response.status_code} {response.kind}', ok=True)
            self.notify(f'{slug} → HTTP {response.status_code} ({response.kind})')
        except Exception as exc:
            self.log_event('stack', f'request {slug}', str(exc), ok=False)
            self.notify(f'request failed: {exc}', severity='error')
        self.populate()

    def action_setup(self) -> None:
        if not self.guard():
            return
        self.perform('setup', '', lambda: self.source.setup())

    def action_unregister(self) -> None:
        if not self.guard():
            return
        slug = self.target_slug()
        if not slug:
            self.notify('select or type a slug')
            return
        self.confirm_then(f'Unregister {slug}? removes A + TXT', 'unregister', slug, lambda: self.source.unregister(slug))

    def action_teardown(self) -> None:
        if not self.guard():
            return
        self.confirm_then('Tear down the local edge? deletes DNS + stack state', 'teardown', '', lambda: self.source.teardown())

    # ── carried-over base extras (?, e, t) ──────────────────────────────────────────
    def action_help(self) -> None:
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Help import SG_Edge__TUI__Help
        self.push_screen(SG_Edge__TUI__Help(self.help_lines()))

    def action_export_card(self) -> None:
        if self.snapshot is None:
            return
        from sg_compute_specs.sg_edge.tui.service.SG_Edge__TUI__Card import SG_Edge__TUI__Card
        self.copy_to_clipboard(SG_Edge__TUI__Card().render(self.snapshot))
        self.notify('snapshot card copied to clipboard (OSC-52)')

    def action_toggle_theme(self) -> None:
        self.theme = 'textual-light' if self.theme == 'textual-dark' else 'textual-dark'

    def help_lines(self) -> list:
        seen, lines = set(), []
        for klass in type(self).__mro__:
            if klass.__module__.startswith('textual'):                               # skip the framework's own bindings
                continue
            for binding in klass.__dict__.get('BINDINGS', []):
                if isinstance(binding, (tuple, list)):
                    key, desc = binding[0], (binding[2] if len(binding) > 2 else binding[1])
                else:
                    key, desc = getattr(binding, 'key', ''), (getattr(binding, 'description', '') or getattr(binding, 'action', ''))
                if key and key not in seen:
                    seen.add(key)
                    lines.append((key, desc))
        return lines
