# ═══════════════════════════════════════════════════════════════════════════════
# SG/Compute Specs — sg_edge tui: SG_Edge__TUI__App__Base
# Shared base for every SG/Edge TUI screen. Provides the common keybindings and
# actions so each screen only declares its own (refresh / navigation / filters):
#   q  quit        ?  help overlay (context-aware)    t  toggle dark/light theme
#   e  export the current snapshot as an ASCII card to the clipboard (OSC-52)
#
# Textual's BINDINGS merge across the MRO, so a subclass's keys add to these. The
# export key is `e` (not `c`) to avoid clashing with the Events screen's `c`=clear
# and to match the sibling CF-logs TUI convention.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app import App


class SG_Edge__TUI__App__Base(App):
    BINDINGS = [('q',              'leave',        'Quit'),
                ('question_mark',  'help',         'Help'),
                ('t',              'toggle_theme', 'Theme'),
                ('e',              'export_card',  'Export')]

    def __init__(self):
        super().__init__()
        self.exited = False

    def card_snapshot(self):                                                         # which snapshot the export renders; screens may override
        return getattr(self, 'snapshot', None)

    def help_lines(self) -> list:                                                    # (key, description) over our own MRO BINDINGS — context-aware, excludes Textual defaults
        seen, lines = set(), []
        for klass in type(self).__mro__:
            if not klass.__module__.startswith('sg_compute_specs'):                  # skip textual.App's built-in bindings
                continue
            for binding in klass.__dict__.get('BINDINGS', []):
                if isinstance(binding, (tuple, list)):                               # raw tuple (subclass)
                    key  = binding[0]
                    desc = binding[2] if len(binding) > 2 else binding[1]
                else:                                                                # Textual Binding object (normalised)
                    key  = getattr(binding, 'key', '')
                    desc = getattr(binding, 'description', '') or getattr(binding, 'action', '')
                if key and key not in seen:
                    seen.add(key)
                    lines.append((key, desc))
        return lines

    def action_help(self) -> None:
        from sg_compute_specs.sg_edge.tui.screens.SG_Edge__TUI__Help import SG_Edge__TUI__Help
        self.push_screen(SG_Edge__TUI__Help(self.help_lines()))

    def action_toggle_theme(self) -> None:
        self.theme = 'textual-light' if self.theme == 'textual-dark' else 'textual-dark'

    def action_export_card(self) -> None:
        snapshot = self.card_snapshot()
        if snapshot is None:
            return
        from sg_compute_specs.sg_edge.tui.service.SG_Edge__TUI__Card import SG_Edge__TUI__Card
        self.copy_to_clipboard(SG_Edge__TUI__Card().render(snapshot))                # OSC-52 — survives the SSH/SSM chain
        self.notify('snapshot card copied to clipboard (OSC-52)')

    def action_leave(self) -> None:
        self.exited = True
        self.exit()
