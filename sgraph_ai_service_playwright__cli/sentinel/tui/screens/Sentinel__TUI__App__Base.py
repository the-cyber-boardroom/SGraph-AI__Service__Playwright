# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — Sentinel__TUI__App__Base
# Shared base for every SG/Sentinel TUI screen: q quit / ? context-aware help /
# t toggle theme. Subclass BINDINGS merge across Textual's MRO, so each screen adds
# its own keys (r refresh, ↑/↓, enter, esc). Mirrors the sg_edge TUI base.
# ═══════════════════════════════════════════════════════════════════════════════

from textual.app import App


class Sentinel__TUI__App__Base(App):
    BINDINGS = [('q',             'leave',        'Quit'),
                ('question_mark', 'help',         'Help'),
                ('t',             'toggle_theme', 'Theme')]

    def __init__(self):
        super().__init__()
        self.exited = False

    def help_lines(self) -> list:                                                    # (key, description) over our own MRO BINDINGS — context-aware
        seen, lines = set(), []
        for klass in type(self).__mro__:
            if not klass.__module__.startswith('sgraph_ai_service_playwright__cli'):
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
        return lines

    def action_help(self) -> None:
        from sgraph_ai_service_playwright__cli.sentinel.tui.screens.Sentinel__TUI__Help import Sentinel__TUI__Help
        self.push_screen(Sentinel__TUI__Help(self.help_lines()))

    def action_toggle_theme(self) -> None:
        self.theme = 'textual-light' if self.theme == 'textual-dark' else 'textual-dark'

    def action_leave(self) -> None:
        self.exited = True
        self.exit()
